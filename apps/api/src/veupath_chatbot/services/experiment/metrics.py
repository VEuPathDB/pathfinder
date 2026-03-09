"""Metrics engine for computing exhaustive classification metrics.

Computes all standard binary classification metrics from the raw
intersection counts returned by :func:`run_positive_negative_controls`.
"""

import math

from veupath_chatbot.platform.types import JSONObject, JSONValue
from veupath_chatbot.services.experiment.helpers import safe_int
from veupath_chatbot.services.experiment.types import (
    ConfusionMatrix,
    ExperimentMetrics,
)


def compute_confusion_matrix(
    *,
    positive_hits: int,
    total_positives: int,
    negative_hits: int,
    total_negatives: int,
) -> ConfusionMatrix:
    """Derive a confusion matrix from control-test intersection counts.

    :param positive_hits: Number of positive controls found in results (TP).
    :param total_positives: Total positive controls provided.
    :param negative_hits: Number of negative controls found in results (FP).
    :param total_negatives: Total negative controls provided.
    :returns: Populated confusion matrix.
    """
    tp = positive_hits
    fn = total_positives - positive_hits
    fp = negative_hits
    tn = total_negatives - negative_hits
    return ConfusionMatrix(
        true_positives=max(tp, 0),
        false_positives=max(fp, 0),
        true_negatives=max(tn, 0),
        false_negatives=max(fn, 0),
    )


def compute_metrics(
    cm: ConfusionMatrix,
    *,
    total_results: int = 0,
) -> ExperimentMetrics:
    """Compute all classification metrics from a confusion matrix.

    :param cm: Confusion matrix.
    :param total_results: Total number of results returned by the search.
    :returns: Full metrics object.
    """
    tp, fp, tn, fn = (
        cm.true_positives,
        cm.false_positives,
        cm.true_negatives,
        cm.false_negatives,
    )

    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    f1_denom = precision + sensitivity
    f1 = (2 * precision * sensitivity / f1_denom) if f1_denom > 0 else 0.0

    # Matthews Correlation Coefficient
    mcc_denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn) - (fp * fn)) / mcc_denom if mcc_denom > 0 else 0.0

    balanced_accuracy = (sensitivity + specificity) / 2.0
    youdens_j = sensitivity + specificity - 1.0

    return ExperimentMetrics(
        confusion_matrix=cm,
        sensitivity=sensitivity,
        specificity=specificity,
        precision=precision,
        negative_predictive_value=npv,
        false_positive_rate=fpr,
        false_negative_rate=fnr,
        f1_score=f1,
        mcc=mcc,
        balanced_accuracy=balanced_accuracy,
        youdens_j=youdens_j,
        total_results=total_results,
        total_positives=tp + fn,
        total_negatives=tn + fp,
    )


def evaluate_gene_ids_against_controls(
    *,
    gene_ids: list[str],
    positive_controls: list[str],
    negative_controls: list[str],
    site_id: str = "",
    record_type: str = "",
) -> JSONObject:
    """Evaluate a gene set against controls using pure set intersection.

    No WDK calls — the gene set already has its results.  Returns the
    same dict shape that :func:`metrics_from_control_result` and
    :func:`extract_and_enrich_genes` consume.
    """
    gene_set = set(gene_ids)
    pos = [s.strip() for s in positive_controls if s.strip()]
    neg = [s.strip() for s in negative_controls if s.strip()]

    result: JSONObject = {
        "siteId": site_id,
        "recordType": record_type,
        "target": {"searchName": "__gene_set__", "resultCount": len(gene_ids)},
        "positive": None,
        "negative": None,
    }

    if pos:
        pos_hits: list[JSONValue] = [g for g in pos if g in gene_set]
        pos_missing: list[JSONValue] = [g for g in pos if g not in gene_set]
        result["positive"] = {
            "controlsCount": len(pos),
            "intersectionCount": len(pos_hits),
            "intersectionIds": pos_hits,
            "intersectionIdsSample": pos_hits[:50],
            "targetStepId": None,
            "targetResultCount": len(gene_ids),
            "missingIdsSample": pos_missing[:50],
            "recall": len(pos_hits) / len(pos) if pos else None,
        }

    if neg:
        neg_hits: list[JSONValue] = [g for g in neg if g in gene_set]
        result["negative"] = {
            "controlsCount": len(neg),
            "intersectionCount": len(neg_hits),
            "intersectionIds": neg_hits,
            "intersectionIdsSample": neg_hits[:50],
            "targetStepId": None,
            "targetResultCount": len(gene_ids),
            "unexpectedHitsSample": neg_hits[:50],
            "falsePositiveRate": len(neg_hits) / len(neg) if neg else None,
        }

    return result


def metrics_from_control_result(result: JSONObject) -> ExperimentMetrics:
    """Build metrics from the dict returned by :func:`run_positive_negative_controls`.

    :param result: Raw control-test result dict.
    :returns: Full metrics.
    """
    positive = result.get("positive") or {}
    negative = result.get("negative") or {}
    target = result.get("target") or {}

    pos_data = positive if isinstance(positive, dict) else {}
    neg_data = negative if isinstance(negative, dict) else {}
    tgt_data = target if isinstance(target, dict) else {}

    pos_count = safe_int(pos_data.get("intersectionCount"), 0)
    pos_total = safe_int(pos_data.get("controlsCount"), 0)
    neg_count = safe_int(neg_data.get("intersectionCount"), 0)
    neg_total = safe_int(neg_data.get("controlsCount"), 0)
    total_results = safe_int(tgt_data.get("resultCount"), 0)

    cm = compute_confusion_matrix(
        positive_hits=pos_count,
        total_positives=pos_total,
        negative_hits=neg_count,
        total_negatives=neg_total,
    )
    return compute_metrics(cm, total_results=total_results)
