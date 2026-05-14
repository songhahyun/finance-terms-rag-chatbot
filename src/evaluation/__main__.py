from __future__ import annotations

import argparse

from src.common.config import get_settings
from src.evaluation.ragas_pipeline import run_ragas_evaluation, run_ragas_evaluations


def main() -> None:
    """Parse CLI arguments and run the RAGAS evaluation entry point.
    Print a compact summary after writing detailed outputs to disk."""
    settings = get_settings()
    default_generated_csv_path = settings.eval_output_dir / "generation_001_baseline" / "dense_clova_bge-m3.csv"
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation pipeline")
    parser.add_argument("--generated-csv", nargs="+", default=[str(default_generated_csv_path)])
    parser.add_argument("--chunk-json", default=str(settings.default_chunk_json_path))
    parser.add_argument("--output-csv", default=str(settings.eval_output_dir / "ragas_eval_result.csv"))
    parser.add_argument("--output-summary-csv", default=str(settings.eval_output_dir / "ragas_eval_summary.csv"))
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    parser.add_argument("--judge-embedding-model", default="multilingual-e5-large")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--use-weave", action="store_true")
    parser.add_argument("--weave-project", default="finance-terms-rag-evaluation")
    parser.add_argument("--weave-experiment-group", default=None)
    parser.add_argument("--weave-experiment-name", default=None)
    parser.add_argument("--weave-log-contexts", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--weave-print-call-link", action="store_true")
    args = parser.parse_args()

    if len(args.generated_csv) == 1:
        _, summary = run_ragas_evaluation(
            generated_csv_path=args.generated_csv[0],
            chunk_json_path=args.chunk_json,
            output_csv_path=args.output_csv,
            output_summary_path=args.output_summary_csv,
            judge_model=args.judge_model,
            judge_embedding_model=args.judge_embedding_model,
            max_rows=args.max_rows,
            use_weave=args.use_weave,
            weave_project=args.weave_project,
            weave_experiment_group=args.weave_experiment_group,
            weave_experiment_name=args.weave_experiment_name,
            weave_log_contexts=args.weave_log_contexts,
            weave_print_call_link=args.weave_print_call_link,
        )
    else:
        detail_outputs, summary_df = run_ragas_evaluations(
            generated_csv_paths=args.generated_csv,
            chunk_json_path=args.chunk_json,
            output_dir=settings.eval_output_dir / "ragas_eval_result",
            output_summary_path=args.output_summary_csv,
            judge_model=args.judge_model,
            judge_embedding_model=args.judge_embedding_model,
            max_rows=args.max_rows,
            use_weave=args.use_weave,
            weave_project=args.weave_project,
            weave_experiment_group=args.weave_experiment_group,
            weave_log_contexts=args.weave_log_contexts,
            weave_print_call_link=args.weave_print_call_link,
        )
        summary = {
            "answer_relevancy": float(summary_df["answer_relevancy"].mean()),
            "faithfulness": float(summary_df["faithfulness"].mean()),
            "context_precision": float(summary_df["context_precision"].mean()),
            "context_recall": float(summary_df["context_recall"].mean()),
        }
        print("RAGAS detail outputs")
        for name, path in detail_outputs.items():
            print(f"- {name}: {path}")
    print("RAGAS summary")
    for key, value in summary.items():
        print(f"- {key}: {value:.4f}")
    print(f"generated csv: {args.generated_csv}")
    print(f"detail saved: {args.output_csv}")
    print(f"summary saved: {args.output_summary_csv}")


if __name__ == "__main__":
    main()
