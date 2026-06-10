from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import MarketCandle, Strategy, StrategyAction, StrategyCondition, StrategyRule
from app.schemas.strategy_builder import (
    StrategyBuilderCreate,
    StrategyBuilderRead,
    StrategyConditionEvaluation,
    StrategyEvaluationRequest,
    StrategyEvaluationResponse,
    StrategyRuleCreate,
    StrategyRuleEvaluation,
    StrategyRuleRead,
    StrategyRulesUpdate,
)
from app.schemas.trading import StrategyCreate
from app.services.audit import record_event
from app.services.ai.features import FeatureCalculator
from app.services.repository import create_strategy, list_candles


def create_strategy_builder(db: Session, payload: StrategyBuilderCreate) -> StrategyBuilderRead:
    existing = db.scalar(select(Strategy).where(Strategy.name == payload.name))
    if existing:
        raise ValueError("Strategy name already exists")

    strategy = create_strategy(
        db,
        StrategyCreate(
            name=payload.name,
            description=payload.description,
            timeframe=payload.timeframe,
            status="active" if payload.enabled else "draft",
            enabled=payload.enabled,
            parameters={"source": "strategy_builder"},
        ),
    )
    replace_rules(db, strategy, payload.rules, commit=True)
    return get_strategy_builder(db, strategy.id)  # type: ignore[return-value]


def list_strategy_builders(db: Session) -> list[StrategyBuilderRead]:
    strategies = db.scalars(
        select(Strategy)
        .options(selectinload(Strategy.builder_rules).selectinload(StrategyRule.conditions))
        .options(selectinload(Strategy.builder_rules).selectinload(StrategyRule.actions))
        .order_by(Strategy.created_at.desc())
    ).all()
    return [builder_to_schema(strategy) for strategy in strategies if strategy.builder_rules]


def get_strategy_builder(db: Session, strategy_id: int) -> StrategyBuilderRead | None:
    strategy = db.scalar(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .options(selectinload(Strategy.builder_rules).selectinload(StrategyRule.conditions))
        .options(selectinload(Strategy.builder_rules).selectinload(StrategyRule.actions))
    )
    return builder_to_schema(strategy) if strategy else None


def get_strategy_rules(db: Session, strategy_id: int) -> list[StrategyRuleRead] | None:
    strategy = get_strategy_with_rules(db, strategy_id)
    if strategy is None:
        return None
    return [StrategyRuleRead.model_validate(rule) for rule in strategy.builder_rules]


def update_strategy_rules(db: Session, strategy_id: int, payload: StrategyRulesUpdate) -> list[StrategyRuleRead] | None:
    strategy = get_strategy_with_rules(db, strategy_id)
    if strategy is None:
        return None
    replace_rules(db, strategy, payload.rules, commit=True)
    refreshed = get_strategy_with_rules(db, strategy_id)
    return [StrategyRuleRead.model_validate(rule) for rule in refreshed.builder_rules] if refreshed else None


def evaluate_strategy(
    db: Session,
    strategy_id: int,
    payload: StrategyEvaluationRequest,
) -> StrategyEvaluationResponse | None:
    strategy = get_strategy_with_rules(db, strategy_id)
    if strategy is None:
        return None

    candles = list_candles(db, payload.symbol, payload.timeframe, payload.lookback)
    if len(candles) < 80:
        raise ValueError("Not enough candle data to evaluate strategy")

    context = IndicatorContext(candles)
    evaluations: list[StrategyRuleEvaluation] = []
    selected_action = "HOLD"
    triggered_rule_id: int | None = None

    for rule in sorted(strategy.builder_rules, key=lambda item: item.priority):
        if not rule.enabled:
            continue
        condition_results = [evaluate_condition(condition, context) for condition in rule.conditions]
        triggered = bool(condition_results) and all(result.passed for result in condition_results)
        action = rule.actions[0].action if rule.actions else "HOLD"
        evaluations.append(
            StrategyRuleEvaluation(
                rule_id=rule.id,
                rule_name=rule.name,
                action=action,
                triggered=triggered,
                conditions=condition_results,
            )
        )
        if triggered and triggered_rule_id is None:
            selected_action = action
            triggered_rule_id = rule.id

    return StrategyEvaluationResponse(
        strategy_id=strategy.id,
        strategy_name=strategy.name,
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        action=selected_action,
        triggered_rule_id=triggered_rule_id,
        indicators=context.snapshot(),
        evaluations=evaluations,
        message="Rule triggered." if triggered_rule_id else "No enabled rules matched; defaulting to HOLD.",
    )


def get_strategy_with_rules(db: Session, strategy_id: int) -> Strategy | None:
    return db.scalar(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .options(selectinload(Strategy.builder_rules).selectinload(StrategyRule.conditions))
        .options(selectinload(Strategy.builder_rules).selectinload(StrategyRule.actions))
    )


def replace_rules(db: Session, strategy: Strategy, rules: list[StrategyRuleCreate], commit: bool = False) -> None:
    for existing_rule in list(strategy.builder_rules):
        db.delete(existing_rule)
    db.flush()

    now = datetime.now(timezone.utc)
    for rule_payload in rules:
        rule = StrategyRule(
            strategy_id=strategy.id,
            name=rule_payload.name,
            logic_operator=rule_payload.logic_operator,
            priority=rule_payload.priority,
            enabled=rule_payload.enabled,
            updated_at=now,
        )
        db.add(rule)
        db.flush()
        for index, condition_payload in enumerate(rule_payload.conditions, start=1):
            db.add(
                StrategyCondition(
                    rule_id=rule.id,
                    sequence=condition_payload.sequence or index,
                    indicator=condition_payload.indicator,
                    operator=condition_payload.operator,
                    value=condition_payload.value,
                    period=condition_payload.period,
                    compare_indicator=condition_payload.compare_indicator,
                    compare_period=condition_payload.compare_period,
                    parameters=condition_payload.parameters,
                )
            )
        db.add(
            StrategyAction(
                rule_id=rule.id,
                action=rule_payload.action.action,
                parameters=rule_payload.action.parameters,
            )
        )

    if commit:
        db.commit()
        record_event(
            db,
            event_type="strategy.rules.updated",
            entity_type="strategy",
            entity_id=strategy.id,
            message=f"Updated builder rules for {strategy.name}.",
            metadata={"rule_count": len(rules)},
            commit=True,
        )


def builder_to_schema(strategy: Strategy) -> StrategyBuilderRead:
    return StrategyBuilderRead(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        timeframe=strategy.timeframe,
        status=strategy.status,
        enabled=strategy.enabled,
        rules=[StrategyRuleRead.model_validate(rule) for rule in strategy.builder_rules],
        created_at=strategy.created_at,
    )


def evaluate_condition(condition: StrategyCondition, context: "IndicatorContext") -> StrategyConditionEvaluation:
    left = context.value(condition.indicator, condition.period)
    right = (
        context.value(condition.compare_indicator, condition.compare_period)
        if condition.compare_indicator
        else float(condition.value if condition.value is not None else 0.0)
    )
    return StrategyConditionEvaluation(
        condition_id=condition.id,
        indicator=indicator_label(condition.indicator, condition.period),
        operator=condition.operator,
        left_value=round(left, 6),
        right_value=round(right, 6),
        passed=compare_values(left, condition.operator, right),
    )


def compare_values(left: float, operator: str, right: float) -> bool:
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    return False


def indicator_label(indicator: str, period: int | None = None) -> str:
    return f"{indicator}{period}" if period else indicator


class IndicatorContext:
    def __init__(self, candles: list[MarketCandle]) -> None:
        self.candles = candles
        self.calculator = FeatureCalculator()

    def value(self, indicator: str | None, period: int | None = None) -> float:
        return self.calculator.indicator_value(self.candles, indicator, period)

    def snapshot(self) -> dict[str, float]:
        return self.calculator.builder_snapshot(self.candles)
