import random
from statistics import mean, median

from sqlalchemy.orm import Session

from app.models import MonteCarloRun
from app.schemas.risk import MonteCarloDistributionPoint, MonteCarloRequest, MonteCarloResponse


def run_monte_carlo(db: Session, payload: MonteCarloRequest) -> MonteCarloResponse:
    endings: list[float] = []
    drawdowns: list[float] = []
    ruin_count = 0
    ruin_equity = payload.starting_balance * payload.ruin_threshold

    for _ in range(payload.number_of_simulations):
        equity = payload.starting_balance
        peak = equity
        max_drawdown = 0.0
        for _trade_index in range(payload.number_of_trades):
            risk_amount = equity * payload.risk_per_trade
            if random.random() <= payload.win_rate:
                equity += risk_amount * payload.average_win
            else:
                equity -= risk_amount * payload.average_loss
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown = max(max_drawdown, (peak - equity) / peak)
        endings.append(round(equity, 4))
        drawdowns.append(round(max_drawdown, 6))
        if equity <= ruin_equity:
            ruin_count += 1

    endings.sort()
    drawdowns.sort()
    confidence_intervals = {
        "ending_equity": {
            "p05": percentile(endings, 0.05),
            "p25": percentile(endings, 0.25),
            "p50": percentile(endings, 0.50),
            "p75": percentile(endings, 0.75),
            "p95": percentile(endings, 0.95),
        },
        "drawdown": {
            "p50": percentile(drawdowns, 0.50),
            "p75": percentile(drawdowns, 0.75),
            "p95": percentile(drawdowns, 0.95),
        },
    }
    probability_of_ruin = ruin_count / payload.number_of_simulations
    expected_drawdown = mean(drawdowns) if drawdowns else 0.0
    maximum_drawdown = max(drawdowns) if drawdowns else 0.0
    recommendation = risk_recommendation(probability_of_ruin, expected_drawdown, maximum_drawdown, payload.risk_per_trade)

    run = MonteCarloRun(
        starting_balance=payload.starting_balance,
        win_rate=payload.win_rate,
        average_win=payload.average_win,
        average_loss=payload.average_loss,
        number_of_trades=payload.number_of_trades,
        number_of_simulations=payload.number_of_simulations,
        risk_per_trade=payload.risk_per_trade,
        probability_of_ruin=round(probability_of_ruin, 6),
        expected_drawdown=round(expected_drawdown, 6),
        maximum_drawdown=round(maximum_drawdown, 6),
        best_case=round(max(endings), 4),
        worst_case=round(min(endings), 4),
        median_case=round(median(endings), 4),
        confidence_intervals=confidence_intervals,
        ending_equity_distribution=[point.model_dump() for point in build_distribution(endings)],
        risk_recommendation=recommendation,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return monte_carlo_to_schema(run)


def get_monte_carlo_run(db: Session, run_id: int) -> MonteCarloResponse | None:
    run = db.get(MonteCarloRun, run_id)
    return monte_carlo_to_schema(run) if run else None


def monte_carlo_to_schema(run: MonteCarloRun) -> MonteCarloResponse:
    return MonteCarloResponse(
        id=run.id,
        starting_balance=run.starting_balance,
        win_rate=run.win_rate,
        average_win=run.average_win,
        average_loss=run.average_loss,
        number_of_trades=run.number_of_trades,
        number_of_simulations=run.number_of_simulations,
        risk_per_trade=run.risk_per_trade,
        probability_of_ruin=run.probability_of_ruin,
        expected_drawdown=run.expected_drawdown,
        maximum_drawdown=run.maximum_drawdown,
        best_case=run.best_case,
        worst_case=run.worst_case,
        median_case=run.median_case,
        confidence_intervals=run.confidence_intervals,
        ending_equity_distribution=[
            MonteCarloDistributionPoint.model_validate(point) for point in run.ending_equity_distribution
        ],
        risk_recommendation=run.risk_recommendation,
        created_at=run.created_at,
    )


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, max(0, round((len(values) - 1) * pct)))
    return round(values[index], 4)


def build_distribution(values: list[float], buckets: int = 12) -> list[MonteCarloDistributionPoint]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if low == high:
        return [MonteCarloDistributionPoint(bucket=f"{low:.0f}", count=len(values), min_equity=low, max_equity=high)]
    width = (high - low) / buckets
    counts = [0 for _ in range(buckets)]
    for value in values:
        index = min(buckets - 1, int((value - low) / width))
        counts[index] += 1
    points = []
    for index, count in enumerate(counts):
        bucket_min = low + (width * index)
        bucket_max = bucket_min + width
        points.append(
            MonteCarloDistributionPoint(
                bucket=f"{bucket_min:.0f}-{bucket_max:.0f}",
                count=count,
                min_equity=round(bucket_min, 4),
                max_equity=round(bucket_max, 4),
            )
        )
    return points


def risk_recommendation(probability_of_ruin: float, expected_drawdown: float, maximum_drawdown: float, risk_per_trade: float) -> str:
    if probability_of_ruin > 0.15 or maximum_drawdown > 0.5:
        return "High risk: reduce risk per trade, improve win/loss profile, or lower trade frequency before deployment."
    if probability_of_ruin > 0.05 or expected_drawdown > 0.25:
        return "Moderate risk: consider smaller sizing or tighter strategy filters before increasing allocation."
    if risk_per_trade > 0.03:
        return "Acceptable simulation profile, but risk per trade is aggressive; scale carefully."
    return "Risk profile is acceptable under the simulated assumptions."
