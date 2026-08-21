import os
import re
import logging
import traceback
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ERROR_PATTERNS = {
    "ImportError": {
        "pattern": r"cannot import name '(\w+)' from '([^']+)'",
        "analysis": "O módulo '{1}' existe mas não contém o nome '{0}'.",
        "fix_suggestion": "Verifique se o nome '{0}' está exportado em {1}.__init__.py",
    },
    "ModuleNotFoundError": {
        "pattern": r"No module named '([^']+)'",
        "analysis": "O módulo '{0}' não está instalado ou não existe.",
        "fix_suggestion": "Execute: pip install {0} ou verifique o nome do módulo",
    },
    "AttributeError": {
        "pattern": r"'(\w+)' object has no attribute '(\w+)'",
        "analysis": "O objeto '{0}' não possui o atributo '{1}'.",
        "fix_suggestion": "Verifique se '{1}' existe em {0} ou se há typo",
    },
    "KeyError": {
        "pattern": r"'([^']+)'",
        "analysis": "A chave '{0}' não existe no dicionário.",
        "fix_suggestion": "Verifique se a chave '{0}' é usada corretamente",
    },
    "TypeError": {
        "pattern": r"(\w+)\(\) (?:missing|unexpected|takes|got)",
        "analysis": "Chamada incorreta de função: {0}.",
        "fix_suggestion": "Verifique os argumentos passados para {0}()",
    },
    "ValueError": {
        "pattern": r".+",
        "analysis": "Valor inválido fornecido.",
        "fix_suggestion": "Verifique os dados de entrada",
    },
    "IndexError": {
        "pattern": r"index (?:out of range|is not valid)",
        "analysis": "Acesso a índice inexistente em sequência.",
        "fix_suggestion": "Verifique o tamanho da sequência antes de acessar",
    },
    "FileNotFoundError": {
        "pattern": r"No such file or directory: '([^']+)'",
        "analysis": "Arquivo '{0}' não encontrado.",
        "fix_suggestion": "Verifique se o caminho '{0}' está correto",
    },
    "SyntaxError": {
        "pattern": r".+",
        "analysis": "Erro de sintaxe no código Python.",
        "fix_suggestion": "Revise a linha indicada no traceback",
    },
    "RuntimeError": {
        "pattern": r".+",
        "analysis": "Erro em tempo de execução.",
        "fix_suggestion": "Analise o contexto do erro no traceback",
    },
}


@dataclass
class ErrorAnalysis:
    error_type: str
    error_value: str
    file_path: str = ""
    line_number: int = 0
    function_name: str = ""
    source_context: str = ""
    analysis: str = ""
    fix_suggestion: str = ""
    relevant_files: list = field(default_factory=list)


def _parse_traceback(tb_str: str) -> tuple[str, int, str, str]:
    frames = re.findall(
        r'File "([^"]+)", line (\d+)(?:, in (\w+))?\n\s+(.+?)(?:\n|$)',
        tb_str
    )
    if not frames:
        return "", 0, "", ""

    project_frames = [
        (f, int(l), fn, code)
        for f, l, fn, code in frames
        if BASE_DIR in f and "site-packages" not in f
    ]

    if not project_frames:
        project_frames = [(f, int(l), fn, code) for f, l, fn, code in frames]

    if project_frames:
        f, l, fn, code = project_frames[-1]
        return f, l, fn, code.strip()

    return "", 0, "", ""


def _read_source_context(file_path: str, line_number: int, context_lines: int = 10) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        result = []
        for i in range(start, end):
            marker = ">>>" if i == line_number - 1 else "   "
            result.append(f"{marker} {i+1:4d} | {lines[i].rstrip()}")
        return "\n".join(result)
    except Exception as e:
        logger.warning("Could not read %s: %s", file_path, e)
        return ""


def _match_error_pattern(error_type: str, error_value: str) -> tuple[str, str]:
    pattern_info = ERROR_PATTERNS.get(error_type)
    if not pattern_info:
        return "Erro desconhecido.", "Analise o traceback para entender a causa."

    m = re.search(pattern_info["pattern"], error_value)
    if m:
        groups = m.groups()
        try:
            analysis = pattern_info["analysis"].format(*groups)
            fix = pattern_info["fix_suggestion"].format(*groups)
            return analysis, fix
        except (IndexError, KeyError):
            pass

    return pattern_info["analysis"], pattern_info["fix_suggestion"]


def _find_imports(file_path: str) -> list[str]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        imports = re.findall(r'(?:from|import)\s+(\w[\w.]*)', content)
        return imports
    except Exception:
        return []


def _find_related_files(file_path: str, imports: list[str]) -> list[str]:
    related = []
    for imp in imports[:5]:
        parts = imp.split(".")
        if len(parts) >= 2:
            potential = os.path.join(BASE_DIR, *parts[:-1], parts[-1] + ".py")
            if os.path.exists(potential) and potential != file_path:
                related.append(potential)
            potential2 = os.path.join(BASE_DIR, *parts, "__init__.py")
            if os.path.exists(potential2):
                related.append(potential2)
    return list(set(related))[:5]


def analyze_error(error_type: str, error_value: str, traceback_str: str = "") -> ErrorAnalysis:
    analysis = ErrorAnalysis(
        error_type=error_type,
        error_value=error_value,
    )

    if traceback_str:
        file_path, line_number, function_name, _ = _parse_traceback(traceback_str)
        analysis.file_path = file_path
        analysis.line_number = line_number
        analysis.function_name = function_name

        if file_path and line_number:
            analysis.source_context = _read_source_context(file_path, line_number)
            analysis.relevant_files = _find_related_files(file_path, _find_imports(file_path))

    text_analysis, fix_suggestion = _match_error_pattern(error_type, error_value)
    analysis.analysis = text_analysis
    analysis.fix_suggestion = fix_suggestion

    logger.info("Analyzed %s in %s:%d", error_type, analysis.file_path, analysis.line_number)
    return analysis


def format_analysis_for_telegram(analysis: ErrorAnalysis) -> str:
    parts = [f"*{analysis.error_type}:* {analysis.error_value[:200]}"]

    if analysis.file_path:
        rel_path = os.path.relpath(analysis.file_path, BASE_DIR)
        parts.append(f"*Arquivo:* `{rel_path}:{analysis.line_number}`")

    if analysis.function_name:
        parts.append(f"*Função:* `{analysis.function_name}()`")

    if analysis.analysis:
        parts.append(f"\n*Análise:* {analysis.analysis}")

    if analysis.fix_suggestion:
        parts.append(f"*Sugestão:* {analysis.fix_suggestion}")

    if analysis.source_context:
        truncated = analysis.source_context[:600]
        if len(analysis.source_context) > 600:
            truncated += "\n  ..."
        parts.append(f"*Código:*\n```\n{truncated}\n```")

    return "\n".join(parts)
