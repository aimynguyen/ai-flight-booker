import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
LOG_DIR = HERE / "logs"

QUESTION = (
    "Trong tất cả file log, service nào có nhiều timeout nhất? "
    "Cho biết số lượng và tối đa 3 timestamp mẫu."
)

LOG_PATTERN = re.compile(
    r"(?P<timestamp>\S+)\s+service=(?P<service>\S+)\s+event=(?P<event>\S+)"
)


def read_log_files() -> list[Path]:
    """Chỉ đọc file .log trong thư mục fixture đã định sẵn."""
    if not LOG_DIR.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục log: {LOG_DIR}")

    files = sorted(LOG_DIR.glob("*.log"))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy file .log trong {LOG_DIR}")

    return files


def execute_program(program_json: str) -> str:
    """Diễn giải chương trình JSON giới hạn, không chạy Python tùy ý."""
    try:
        program = json.loads(program_json)
    except json.JSONDecodeError as error:
        raise ValueError("Chương trình do model gửi không phải JSON hợp lệ.") from error

    steps = program.get("steps")
    if not isinstance(steps, list) or len(steps) != 2:
        raise ValueError("Chương trình phải có đúng hai bước được cho phép.")

    if steps[0] != {"tool": "list_logs"}:
        raise ValueError("Bước đầu tiên phải là list_logs.")

    query = steps[1]
    if not isinstance(query, dict):
        raise ValueError("Bước đếm log phải là một object JSON.")

    if query.get("tool") != "count_events":
        raise ValueError("Chỉ cho phép tool count_events.")

    if query.get("event") != "timeout" or query.get("group_by") != "service":
        raise ValueError("Demo chỉ cho phép đếm timeout theo service.")

    max_samples = query.get("max_samples")
    if not isinstance(max_samples, int) or not 1 <= max_samples <= 3:
        raise ValueError("max_samples phải là số nguyên từ 1 đến 3.")

    # Bước 1: runtime liệt kê file trong thư mục fixture.
    files = read_log_files()

    # Bước 2: runtime đọc và tổng hợp từng dòng; không trả dòng log thô.
    counts: dict[str, int] = {}
    timestamps: dict[str, list[str]] = {}

    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = LOG_PATTERN.search(line)
            if not match or match.group("event") != "timeout":
                continue

            service = match.group("service")
            counts[service] = counts.get(service, 0) + 1
            timestamps.setdefault(service, []).append(match.group("timestamp"))

    if not counts:
        raise ValueError("Không tìm thấy event timeout trong các file log.")

    top_service = sorted(counts, key=lambda service: (-counts[service], service))[0]

    result = {
        "files_scanned": len(files),
        "timeout_counts": counts,
        "top_service": top_service,
        "top_service_count": counts[top_service],
        "sample_timestamps": timestamps[top_service][:max_samples],
    }

    return json.dumps(result, ensure_ascii=False)


@tool
def run_code(program_json: str) -> str:
    """Run an allow-listed program over the fixture logs and return summary only.

    The program must be JSON with two steps:
    list_logs, then count_events(event="timeout", group_by="service",
    max_samples between 1 and 3).
    """
    return execute_program(program_json)


def get_input_tokens(response: Any) -> int | None:
    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict):
        tokens = usage.get("input_tokens")
        if isinstance(tokens, int):
            return tokens
    return None


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "Không tìm thấy Gemini API key trong biến môi trường hoặc file .env."
        )

    if not read_log_files():
        raise ValueError("Cần ít nhất một file log để chạy demo.")

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        api_key=api_key,
    )

    # Baseline: log thô được gửi vào context của model.
    raw_logs = "\n".join(
        f"FILE: {path.name}\n{path.read_text(encoding='utf-8')}"
        for path in read_log_files()
    )
    direct_response = llm.invoke([
        SystemMessage(
            content="Answer the question using the supplied logs. "
                    "Return the service, count, and up to 3 timestamps."
        ),
        HumanMessage(content=f"{QUESTION}\n\nLOGS:\n{raw_logs}"),
    ])

    print("===== BASELINE: RAW LOGS SENT TO MODEL =====")
    print(direct_response.content)
    direct_tokens = get_input_tokens(direct_response)
    print(f"Input tokens: {direct_tokens if direct_tokens is not None else 'unavailable'}")

    # Code Mode: model nhận câu hỏi và tool description, không nhận raw logs.
    code_model = llm.bind_tools([run_code])
    tool_request = code_model.invoke([
        SystemMessage(
            content=(
                "Answer the user by calling run_code exactly once. "
                "Pass program_json as a JSON string containing these two steps: "
                '{"steps":[{"tool":"list_logs"},{"tool":"count_events",'
                '"event":"timeout","group_by":"service","max_samples":3}]}. '
                "Do not request or reproduce raw log lines."
            )
        ),
        HumanMessage(content=QUESTION),
    ])

    calls = getattr(tool_request, "tool_calls", [])
    if len(calls) != 1 or calls[0].get("name") != "run_code":
        raise RuntimeError(
            "Model không gọi run_code đúng yêu cầu. Hãy xem lại tool call."
        )

    call = calls[0]
    tool_result = run_code.invoke(call["args"])

    # Kiểm tra output tool chỉ là kết quả tổng hợp, không phải raw log.
    if "service=" in tool_result or "event=" in tool_result:
        raise RuntimeError("Tool output chứa nội dung log thô; không gửi tiếp cho model.")

    print("\n===== CODE MODE: TOOL SUMMARY =====")
    print(tool_result)

    final_response = llm.invoke([
        SystemMessage(content="Answer the user using only the tool summary."),
        HumanMessage(content=QUESTION),
        tool_request,
        ToolMessage(content=tool_result, tool_call_id=call["id"]),
    ])

    print("\n===== CODE MODE: FINAL ANSWER =====")
    print(final_response.content)

    request_tokens = get_input_tokens(tool_request)
    final_tokens = get_input_tokens(final_response)
    if request_tokens is not None and final_tokens is not None:
        print(
            "\nCode Mode input tokens "
            f"(tool request + final answer): {request_tokens + final_tokens}"
        )
    else:
        print("\nCode Mode input tokens: usage metadata unavailable.")


if __name__ == "__main__":
    main()