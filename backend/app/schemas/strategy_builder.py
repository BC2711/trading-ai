from datetime import datetime

from pydantic import BaseModel, Field, model_validator

SUPPORTED_INDICATOR_PATTERN = "^(RSI|MACD|EMA|SMA|BOLLINGER_BANDS|ATR|VOLUME|PRICE_CHANGE)$"
SUPPORTED_OPERATOR_PATTERN = "^(<|<=|>|>=|==|!=)$"
SUPPORTED_ACTION_PATTERN = "^(BUY|SELL|HOLD|CLOSE_POSITION)$"


class StrategyConditionBase(BaseModel):
    indicator: str = Field(default="RSI", pattern=SUPPORTED_INDICATOR_PATTERN)
    operator: str = Field(default="<", pattern=SUPPORTED_OPERATOR_PATTERN)
    value: float | None = None
    period: int | None = Field(default=None, ge=1, le=500)
    compare_indicator: str | None = Field(default=None, pattern=SUPPORTED_INDICATOR_PATTERN)
    compare_period: int | None = Field(default=None, ge=1, le=500)
    parameters: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target(self) -> "StrategyConditionBase":
        if self.value is None and self.compare_indicator is None:
            raise ValueError("Condition requires either a numeric value or compare_indicator")
        return self


class StrategyConditionCreate(StrategyConditionBase):
    sequence: int = Field(default=1, ge=1)


class StrategyConditionRead(StrategyConditionBase):
    id: int
    sequence: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyActionCreate(BaseModel):
    action: str = Field(default="BUY", pattern=SUPPORTED_ACTION_PATTERN)
    parameters: dict = Field(default_factory=dict)


class StrategyActionRead(StrategyActionCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyRuleCreate(BaseModel):
    name: str = Field(default="Entry rule", min_length=2, max_length=160)
    logic_operator: str = Field(default="AND", pattern="^(AND)$")
    priority: int = Field(default=1, ge=1, le=1000)
    enabled: bool = True
    conditions: list[StrategyConditionCreate] = Field(default_factory=list, min_length=1)
    action: StrategyActionCreate = Field(default_factory=StrategyActionCreate)


class StrategyRuleRead(BaseModel):
    id: int
    strategy_id: int
    name: str
    logic_operator: str
    priority: int
    enabled: bool
    conditions: list[StrategyConditionRead] = Field(default_factory=list)
    actions: list[StrategyActionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyBuilderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    timeframe: str = Field(default="15m", max_length=8)
    enabled: bool = False
    rules: list[StrategyRuleCreate] = Field(default_factory=list, min_length=1)


class StrategyBuilderRead(BaseModel):
    id: int
    name: str
    description: str
    timeframe: str
    status: str
    enabled: bool
    rules: list[StrategyRuleRead] = Field(default_factory=list)
    created_at: datetime


class StrategyRulesUpdate(BaseModel):
    rules: list[StrategyRuleCreate] = Field(default_factory=list, min_length=1)


class StrategyEvaluationRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    lookback: int = Field(default=240, ge=30, le=1000)


class StrategyConditionEvaluation(BaseModel):
    condition_id: int
    indicator: str
    operator: str
    left_value: float
    right_value: float
    passed: bool


class StrategyRuleEvaluation(BaseModel):
    rule_id: int
    rule_name: str
    action: str
    triggered: bool
    conditions: list[StrategyConditionEvaluation]


class StrategyEvaluationResponse(BaseModel):
    strategy_id: int
    strategy_name: str
    symbol: str
    timeframe: str
    action: str
    triggered_rule_id: int | None = None
    indicators: dict[str, float]
    evaluations: list[StrategyRuleEvaluation]
    message: str
