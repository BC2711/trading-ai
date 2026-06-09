from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score


class ModelEvaluationService:
    def evaluate(self, labels: list[int], predictions: list[int], probabilities: list[float]) -> dict:
        metrics = {
            "accuracy": round(float(accuracy_score(labels, predictions)), 6),
            "precision": round(float(precision_score(labels, predictions, zero_division=0)), 6),
            "recall": round(float(recall_score(labels, predictions, zero_division=0)), 6),
            "f1": round(float(f1_score(labels, predictions, zero_division=0)), 6),
            "samples": len(labels),
            "confidence": round(float(max(probabilities[-1], 1 - probabilities[-1])), 6) if probabilities else 0.0,
        }
        if len(set(labels)) > 1 and probabilities:
            metrics["roc_auc"] = round(float(roc_auc_score(labels, probabilities)), 6)
        else:
            metrics["roc_auc"] = 0.0
        return metrics
