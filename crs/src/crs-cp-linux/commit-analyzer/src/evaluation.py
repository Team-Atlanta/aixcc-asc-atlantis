from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict


class Evaluator(ABC):
    def eval_accuracy(
        self, vuln_pred, vuln_gt, all_changes, print_results=True
    ) -> Dict:
        total = 0
        vuln_matrix = defaultdict(int)
        tp_matrix = defaultdict(int)
        fp_matrix = defaultdict(int)

        non_vuln = "non-vulnerable"
        gt_labels = set(vuln_gt.values()) | set([non_vuln])
        pred_labels = (
            set(vuln_gt.values())
            | set(element for sublist in vuln_pred.values() for element in sublist)
            | set([non_vuln])
        )
        pred_labels = sorted(pred_labels)
        gt_labels = sorted(gt_labels)
        conf_matrix = {
            label: {label: 0 for label in pred_labels} for label in gt_labels
        }

        for commit, _ in all_changes.items():
            total += 1
            if commit in vuln_gt:
                gt = vuln_gt[commit]
                vuln_matrix[gt] += 1

                if commit in vuln_pred:
                    preds = vuln_pred[commit]
                    for pred in preds:
                        conf_matrix[gt][pred] += 1
                else:
                    preds = [non_vuln]
                    conf_matrix[gt][non_vuln] += 1
            else:
                gt = non_vuln
                vuln_matrix[non_vuln] += 1
                if commit in vuln_pred:
                    preds = vuln_pred[commit]
                    for pred in preds:
                        conf_matrix[non_vuln][pred] += 1
                else:
                    preds = [non_vuln]
                    conf_matrix[non_vuln][non_vuln] += 1
            self.compare(preds, gt, tp_matrix, fp_matrix)

        if print_results:
            for label, count in vuln_matrix.items():
                print("\ntrue class: ", label, count)
                for pred_label, pred_count in conf_matrix[label].items():
                    print(pred_label, f"{pred_count/count:.2f} ({pred_count}/{count})")

        metrics = defaultdict(dict)
        for san_id, num_p in vuln_matrix.items():
            num_n = total - num_p

            tp = tp_matrix[san_id]
            fp = fp_matrix[san_id]
            fn = num_p - tp
            tn = num_n - fp
            accuracy = (tp + tn) / total if total > 0 else -1
            tpr = tp / num_p if num_p > 0 else -1
            fnr = fn / num_p if num_p > 0 else -1
            fpr = fp / num_n if num_n > 0 else -1
            tnr = tn / num_n if num_n > 0 else -1

            if print_results:
                print(f"\nSanitizer {san_id}:")
                print(f"Accuracy: {accuracy:.2f} ({tp + tn}/{total})")
                print(f"TPR: {tpr:.2f} ({tp}/{num_p})")
                print(f"FNR: {fnr:.2f} ({fn}/{num_p})")
                print(f"TNR: {tnr:.2f} ({tn}/{num_n})")
                print(f"FPR: {fpr:.2f} ({fp}/{num_n})")

            metrics[san_id] = {
                "accuracy": f"{accuracy:.2f} ({tp + tn}/{total})",
                "tpr": f"{tpr:.2f} ({tp}/{num_p})",
                "fnr": f"{fnr:.2f} ({fn}/{num_p})",
                "tnr": f"{tnr:.2f} ({tn}/{num_n})",
                "fpr": f"{fpr:.2f} ({fp}/{num_n})",
            }

        return metrics

    @abstractmethod
    def compare(self, preds: list, gt: str, tp_matrix, fp_matrix):
        pass


class StrictEvaluator(Evaluator):
    def compare(self, preds, gt, tp_matrix, fp_matrix):
        if [gt] == preds:
            tp_matrix[gt] += 1
        else:
            for pred in preds:
                fp_matrix[pred] += 1


class BasicEvaluator(Evaluator):
    def compare(self, preds, gt, tp_matrix, fp_matrix):
        if gt in preds:
            tp_matrix[gt] += 1
        else:
            for pred in preds:
                fp_matrix[pred] += 1


class SemanticEvaluator(Evaluator):
    def compare(self, pred, gt, tp_matrix, fp_matrix):
        # Return true if pred contains similar sanitizers as gt
        pass
