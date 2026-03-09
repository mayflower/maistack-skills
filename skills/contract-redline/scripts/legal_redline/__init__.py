"""legal-redline-tools: Apply tracked changes and generate redline PDFs."""

# Vendored from evolsb/legal-redline-tools at commit
# f81f6763bef10e6b1357e557d1cd1602f9ef47fb.

__version__ = "0.2.0"

from legal_redline.apply import apply_redlines
from legal_redline.compare import compare_agreements, format_comparison_report
from legal_redline.diff import diff_documents
from legal_redline.markdown import generate_markdown
from legal_redline.memo import generate_memo_pdf
from legal_redline.remap import remap_redlines
from legal_redline.render import render_redline_pdf
from legal_redline.scan import scan_document
from legal_redline.summary import generate_summary_pdf
