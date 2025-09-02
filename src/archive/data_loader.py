"""Data loaders for VNBdigitaler matching system."""

import json
import logging
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

try:
    from .config import get_settings
    from .matching_models import BDEWCompany, BNetzACompany
    from .models import Company
except ImportError:
    # When run as script, use absolute imports
    from src.config import get_settings
    from src.matching_models import BDEWCompany, BNetzACompany
    from src.models import Company

logger = logging.getLogger(__name__)


class DataLoader:
    """Load data from various sources into matching models."""

    def __init__(self) -> None:
        """Initialize data loader."""
        self.settings = get_settings()
        self.engine = create_async_engine(self.settings.database_url)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession)

    async def load_bdew_companies_from_db(self) -> list[BDEWCompany]:
        """Load BDEW companies from database."""
        logger.info("Loading BDEW companies from database...")

        async with self.session_factory() as session:
            result = await session.execute(
                select(
                    Company.bdew_code,
                    Company.bdew_name,
                    Company.bdew_city,
                    Company.bdew_name_normalized,
                )
            )
            rows = result.fetchall()

        companies = []
        for row in rows:
            company = BDEWCompany(
                bdew_code=row.bdew_code,
                name=row.bdew_name,
                city=row.bdew_city,
                normalized_name=row.bdew_name_normalized,
            )
            companies.append(company)

        logger.info(f"Loaded {len(companies)} BDEW companies from database")
        return companies

    def load_bnetza_companies_from_csv(self, csv_path: Path) -> list[BNetzACompany]:
        """Load BNetzA companies from CSV file."""
        logger.info(f"Loading BNetzA companies from CSV: {csv_path}")

        df = pd.read_csv(csv_path)
        companies = []

        for idx, (_, row) in enumerate(df.iterrows()):
            # Handle different possible column names
            original_name = ""
            rollout_quote = None

            # Try different column name variations
            if "original_name" in row:
                original_name = row["original_name"]
            elif "company_name" in row:
                original_name = row["company_name"]
            elif "name" in row:
                original_name = row["name"]
            else:
                # Use the first string column as name
                for col in df.columns:
                    if df[col].dtype == "object" and pd.notna(row[col]):
                        original_name = str(row[col])
                        break

            # Try to get rollout quote
            if "ausstattungsquote" in row:
                quote_val = row["ausstattungsquote"]
                if pd.notna(quote_val) and quote_val != "":
                    try:
                        rollout_quote = float(quote_val)
                    except (ValueError, TypeError):
                        rollout_quote = None
            elif "rollout_quote" in row:
                quote_val = row["rollout_quote"]
                if pd.notna(quote_val) and quote_val != "":
                    try:
                        rollout_quote = float(quote_val)
                    except (ValueError, TypeError):
                        rollout_quote = None

            if original_name.strip():
                company = BNetzACompany(
                    index=idx,
                    original_name=original_name.strip(),
                    rollout_quote=rollout_quote,
                )
                companies.append(company)

        logger.info(f"Loaded {len(companies)} BNetzA companies from CSV")
        return companies

    def load_bdew_companies_from_csv(self, csv_path: Path) -> list[BDEWCompany]:
        """Load BDEW companies from CSV file."""
        logger.info(f"Loading BDEW companies from CSV: {csv_path}")

        df = pd.read_csv(csv_path)
        companies = []

        for _index, row in df.iterrows():
            # Handle different possible column names
            bdew_code = ""
            name = ""
            city = None

            # Try to get BDEW code
            if "bdew_code" in row:
                bdew_code = str(row["bdew_code"])
            elif "code" in row:
                bdew_code = str(row["code"])
            elif "id" in row:
                bdew_code = str(row["id"])

            # Try to get company name
            if "original_name" in row:
                name = row["original_name"]
            elif "name" in row:
                name = row["name"]
            elif "company_name" in row:
                name = row["company_name"]
            elif "bdew_name" in row:
                name = row["bdew_name"]

            # Try to get city
            if "city" in row and pd.notna(row["city"]):
                city = row["city"]
            elif "bdew_city" in row and pd.notna(row["bdew_city"]):
                city = row["bdew_city"]

            if bdew_code and name:
                company = BDEWCompany(
                    bdew_code=bdew_code,
                    name=name.strip(),
                    city=city.strip() if city else None,
                )
                companies.append(company)

        logger.info(f"Loaded {len(companies)} BDEW companies from CSV")
        return companies

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


def export_matches_to_csv(matches: list[Any], output_path: Path) -> None:
    """Export matches to CSV file."""
    logger.info(f"Exporting {len(matches)} matches to: {output_path}")

    # Convert matches to dictionaries
    data = []
    for match in matches:
        if hasattr(match, "to_dict"):
            data.append(match.to_dict())
        else:
            # Handle other match types if needed
            data.append(match)

    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)

    logger.info(f"Successfully exported matches to {output_path}")


def export_companies_to_csv(companies: list[Any], output_path: Path) -> None:
    """Export companies to CSV file."""
    logger.info(f"Exporting {len(companies)} companies to: {output_path}")

    # Convert companies to dictionaries
    data = []
    for company in companies:
        if isinstance(company, BNetzACompany):
            data.append(
                {
                    "bnetza_index": company.index,
                    "original_name": company.original_name,
                    "normalized_name": company.normalized_name,
                    "rollout_quote": company.rollout_quote or "",
                }
            )
        elif isinstance(company, BDEWCompany):
            data.append(
                {
                    "bdew_code": company.bdew_code,
                    "original_name": company.name,
                    "city": company.city or "",
                    "normalized_name": company.normalized_name,
                }
            )
        else:
            # Handle other company types - ensure dict format
            company_data = (
                company.__dict__
                if hasattr(company, "__dict__")
                else {"name": str(company)}
            )
            data.append(company_data)

    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)

    logger.info(f"Successfully exported companies to {output_path}")


if __name__ == "__main__":
    import argparse
    import json
    import platform
    import re
    import socket
    import subprocess
    import sys
    import time
    from datetime import datetime

    try:
        from src.bnetza.rollout_report_updater import RolloutReportUpdater
    except ImportError:
        # Fallback if import fails
        RolloutReportUpdater = None  # type: ignore[assignment, misc]

    # State file management
    STATE_FILE = "rollout_workflow_state.json"

    def execute_and_time(func, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Execute a function and return its result with execution time.

        Führt eine gegebene Funktion mit ihren Argumenten aus und gibt ein Tupel zurück,
        das das Ergebnis der Funktion und ihre Ausführungszeit in Sekunden enthält.

        Args:
            func (callable): Die Funktion, die ausgeführt werden soll.
            *args: Variable Positionsargumente, die an die Funktion übergeben werden.
            **kwargs: Variable Schlüsselwortargumente, die an die Funktion übergeben werden.

        Returns:
            tuple: Ein Tupel (result, execution_time_seconds). Im Falle eines Fehlers
                   wird die Ausnahme innerhalb des Wrappers abgefangen und geloggt,
                   bevor sie erneut ausgelöst wird.
        """
        start_time = time.perf_counter()
        result = None
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            # Hier könnte man detailliertes Logging einfügen
            print(f"Fehler bei Ausführung von '{func.__name__}': {e}")
            raise  # Den Fehler erneut auslösen, wenn der Workflow unterbrochen werden soll

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        return result, execution_time

    def format_duration(seconds: float) -> str:
        """Format duration in a human-readable way."""
        # Time constants
        SECONDS_PER_MINUTE = 60
        SECONDS_PER_HOUR = 3600

        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < SECONDS_PER_MINUTE:
            return f"{seconds:.1f}s"
        elif seconds < SECONDS_PER_HOUR:
            minutes, secs = divmod(seconds, SECONDS_PER_MINUTE)
            return f"{int(minutes)}m {secs:.0f}s"
        else:
            hours, remainder = divmod(seconds, SECONDS_PER_HOUR)
            minutes, secs = divmod(remainder, SECONDS_PER_MINUTE)
            return f"{int(hours)}h {int(minutes)}m {secs:.0f}s"

    def create_initial_state() -> dict:
        """Create initial state JSON structure."""
        return {
            "workflow": {
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "status": "running",
                "action_type": "unknown",
                "overall_result": None,
            },
            "steps": {
                "discover": {
                    "status": "pending",
                    "completed_at": None,
                    "execution_time_seconds": None,
                    "execution_time_formatted": None,
                    "reports_found": False,
                    "error": None,
                },
                "download": {
                    "status": "pending",
                    "completed_at": None,
                    "execution_time_seconds": None,
                    "execution_time_formatted": None,
                    "files_downloaded": [],
                    "download_count": 0,
                    "error": None,
                },
                "convert": {
                    "status": "pending",
                    "completed_at": None,
                    "execution_time_seconds": None,
                    "execution_time_formatted": None,
                    "files_converted": [],
                    "convert_count": 0,
                    "error": None,
                },
                "import": {
                    "status": "pending",
                    "completed_at": None,
                    "execution_time_seconds": None,
                    "execution_time_formatted": None,
                    "companies_imported": 0,
                    "error": None,
                },
                "company_update": {
                    "status": "pending",
                    "completed_at": None,
                    "execution_time_seconds": None,
                    "execution_time_formatted": None,
                    "companies_processed": 0,
                    "companies_updated": 0,
                    "companies_new": 0,
                    "error": None,
                },
                "quota_update": {
                    "status": "pending",
                    "completed_at": None,
                    "execution_time_seconds": None,
                    "execution_time_formatted": None,
                    "quotas_total": 0,
                    "error": None,
                },
            },
            "report": {
                "filename": None,
                "url": None,
                "quarter": None,
                "year": None,
                "size_bytes": None,
                "downloaded_at": None,
            },
            "files": {"excel_files": [], "csv_files": [], "summary_file": None},
            "statistics": {
                "total_runtime_seconds": 0,
                "peak_memory_mb": 0,
                "errors_count": 0,
                "warnings_count": 0,
            },
            "metadata": {
                "version": "1.0",
                "created_by": "data_loader",
                "python_version": platform.python_version(),
                "hostname": socket.gethostname(),
                "working_directory": str(Path.cwd()),
            },
        }

    def load_state() -> dict[str, Any]:
        """Load state from JSON file or create new one."""
        try:
            if Path(STATE_FILE).exists():
                with Path(STATE_FILE).open() as f:
                    return json.load(f)  # type: ignore[no-any-return]
            else:
                return create_initial_state()
        except Exception as e:
            print(f"⚠️ Error loading state: {e}")
            return create_initial_state()

    def save_state(state: dict) -> None:
        """Save state to JSON file."""
        try:
            with Path(STATE_FILE).open("w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving state: {e}")

    def update_step_status(
        step_name: str, status: str, execution_time: float | None = None, **kwargs: Any
    ) -> None:
        """Update step status in state file."""
        state = load_state()
        state["steps"][step_name]["status"] = status
        state["steps"][step_name]["completed_at"] = datetime.now().isoformat()

        # Add execution time if provided
        if execution_time is not None:
            state["steps"][step_name]["execution_time_seconds"] = round(
                execution_time, 3
            )
            state["steps"][step_name]["execution_time_formatted"] = format_duration(
                execution_time
            )

        # Update specific step data
        for key, value in kwargs.items():
            if key in state["steps"][step_name]:
                state["steps"][step_name][key] = value

        save_state(state)

    def main() -> None:
        """Main function with CLI argument support."""
        parser = argparse.ArgumentParser(description="Data loader for VNBdigitaler")
        parser.add_argument(
            "--rollout-quota-update",
            action="store_true",
            help="Download and convert BNetzA rollout quota reports (all steps)",
        )
        parser.add_argument(
            "--rollout-discover",
            action="store_true",
            help="Step 1: Discover available BNetzA rollout reports",
        )
        parser.add_argument(
            "--rollout-download",
            action="store_true",
            help="Step 2: Download BNetzA rollout Excel files",
        )
        parser.add_argument(
            "--rollout-convert",
            action="store_true",
            help="Step 3: Convert Excel files to CSV format",
        )
        parser.add_argument(
            "--rollout-import",
            action="store_true",
            help="Step 4: Import CSV data to database",
        )
        parser.add_argument(
            "--rollout-company-update",
            action="store_true",
            help="Step 5: Update companies in database",
        )
        parser.add_argument(
            "--rollout-quota-update-step",
            action="store_true",
            help="Step 6: Update quota records",
        )
        parser.add_argument(
            "--rollout-init",
            action="store_true",
            help="Initialize workflow state file",
        )
        parser.add_argument(
            "--rollout-status",
            action="store_true",
            help="Show current workflow status",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force download even if files already exist",
        )

        args = parser.parse_args()

        # Check if any rollout action was specified
        rollout_actions = [
            args.rollout_quota_update,
            args.rollout_discover,
            args.rollout_download,
            args.rollout_convert,
            args.rollout_import,
            args.rollout_company_update,
            args.rollout_quota_update_step,
            args.rollout_init,
            args.rollout_status,
        ]

        if not any(rollout_actions):
            print("No action specified. Available options:")
            print("  --rollout-init              Initialize workflow state")
            print("  --rollout-quota-update      Complete workflow (all steps)")
            print("  --rollout-discover          Step 1: Discover reports")
            print("  --rollout-download          Step 2: Download Excel files")
            print("  --rollout-convert           Step 3: Convert to CSV")
            print("  --rollout-import            Step 4: Import to database")
            print("  --rollout-company-update    Step 5: Update companies")
            print("  --rollout-quota-update-step Step 6: Update quota records")
            print("  --rollout-status            Show current status")
            return

        # Handle special commands first
        if args.rollout_init:
            _run_init_step()
            return

        if args.rollout_status:
            _run_status_step()
            return

        # Initialize updater if available
        updater = None
        if RolloutReportUpdater is not None:
            updater = RolloutReportUpdater(download_dir="data")

        if updater is None:
            print("❌ Could not import rollout report updater")
            return

        try:
            if args.rollout_quota_update:
                # Complete workflow
                print("📥 Starting complete BNetzA rollout quota workflow...")
                _run_init_step()  # Initialize state
                _run_complete_workflow(updater)

            elif args.rollout_discover:
                # Step 1: Discover reports
                print("🔍 Step 1: Discovering available reports...")
                _run_discover_step(updater)

            elif args.rollout_download:
                # Step 2: Download Excel files
                print("📥 Step 2: Downloading Excel files...")
                _run_download_step(updater, force=args.force)

            elif args.rollout_convert:
                # Step 3: Convert Excel to CSV
                print("🔄 Step 3: Converting Excel to CSV format...")
                _run_convert_step(updater)

            elif args.rollout_import:
                # Step 4: Import CSV to database
                print("💾 Step 4: Importing data to database...")
                _run_import_step(updater)

            elif args.rollout_company_update:
                # Step 5: Update companies
                print("🏢 Step 5: Updating companies in database...")
                _run_company_update_step()

            elif args.rollout_quota_update_step:
                # Step 6: Update quota records
                print("📊 Step 6: Updating quota records...")
                _run_quota_update_step()

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            # Update state with error
            state = load_state()
            state["workflow"]["status"] = "failed"
            state["workflow"]["completed_at"] = datetime.now().isoformat()
            state["statistics"]["errors_count"] += 1
            save_state(state)
            sys.exit(1)

    def _run_init_step() -> None:
        """Initialize workflow state file."""
        state = create_initial_state()
        save_state(state)
        print("✅ Workflow state initialized")
        print(f"📁 State file: {STATE_FILE}")

    def _run_status_step() -> None:
        """Show current workflow status."""
        state = load_state()

        print("📊 Current Workflow Status")
        print("=" * 50)
        print(f"Status: {state['workflow']['status']}")
        print(f"Started: {state['workflow']['started_at']}")
        print(f"Action Type: {state['workflow']['action_type']}")

        print("\n🔍 Step Status:")
        for step_name, step_data in state["steps"].items():
            status_icon = {
                "pending": "⏳",
                "running": "🔄",
                "success": "✅",
                "failed": "❌",
                "skipped": "⏭️",
            }.get(step_data["status"], "❓")

            step_line = f"  {status_icon} {step_name}: {step_data['status']}"

            # Add execution time if available
            if step_data.get("execution_time_formatted"):
                step_line += f" ({step_data['execution_time_formatted']})"

            print(step_line)

            if step_data.get("error"):
                print(f"    Error: {step_data['error']}")

        if state["report"]["filename"]:
            print(f"\n📄 Report: {state['report']['filename']}")

        print("\n📁 Files:")
        print(f"  Excel: {len(state['files']['excel_files'])}")
        print(f"  CSV: {len(state['files']['csv_files'])}")

    def _run_complete_workflow(updater: Any) -> None:
        """Run the complete workflow with all steps."""
        print("🔧 Initializing rollout report updater...")

        # Update workflow state
        state = load_state()
        state["workflow"]["action_type"] = "complete_workflow"
        save_state(state)

        # Run all steps
        _run_discover_step(updater)

        # Check if reports were found
        state = load_state()
        if not state["steps"]["discover"]["reports_found"]:
            print("i No new reports found - workflow completed")
            state["workflow"]["status"] = "completed"
            state["workflow"]["overall_result"] = "no_reports_found"
            state["workflow"]["completed_at"] = datetime.now().isoformat()
            save_state(state)
            return

        _run_download_step(updater, force=True)
        _run_convert_step(updater)
        _run_import_step(updater)
        _run_company_update_step()
        _run_quota_update_step()

        # Mark workflow as completed
        state = load_state()
        state["workflow"]["status"] = "completed"
        state["workflow"]["overall_result"] = "success"
        state["workflow"]["completed_at"] = datetime.now().isoformat()
        save_state(state)

        print("✅ All steps completed successfully!")
        print("🎯 Rollout quota data successfully updated!")

    def _run_discover_step(updater: Any) -> None:
        """Run step 1: Discover available reports."""
        update_step_status("discover", "running")

        def _discover() -> Any:
            return updater.discover_report()

        try:
            has_report, execution_time = execute_and_time(_discover)

            if has_report and updater.current_report:
                report_name = updater.current_report.get("filename", "Unknown")
                report_url = updater.current_report.get("url", "Unknown")

                print(
                    f"✅ Found report: {report_name} ({format_duration(execution_time)})"
                )
                print(f"📍 URL: {report_url}")

                # Update state
                state = load_state()
                state["report"]["filename"] = report_name
                state["report"]["url"] = report_url
                save_state(state)

                update_step_status(
                    "discover", "success", execution_time, reports_found=True
                )
            else:
                print(
                    f"i No new reports found - data is up to date ({format_duration(execution_time)})"
                )
                update_step_status(
                    "discover", "success", execution_time, reports_found=False
                )

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Discover failed: {error_msg}")
            update_step_status("discover", "failed", error=error_msg)
            sys.exit(1)

    def _run_download_step(updater: Any, force: bool = False) -> None:
        """Run step 2: Download Excel files."""
        update_step_status("download", "running")

        def _download() -> Any:
            # First discover if not already done
            if not updater.current_report:
                print("🔍 Discovering reports first...")
                has_report = updater.discover_report()
                if not has_report:
                    raise Exception("No reports found to download")

            return updater.download_excel_file(force=force)

        try:
            download_success, execution_time = execute_and_time(_download)

            if download_success:
                print(
                    f"✅ Excel files downloaded successfully ({format_duration(execution_time)})"
                )

                # Find downloaded files
                data_dir = Path("data")
                excel_files = [f.name for f in data_dir.glob("*.xlsx")]

                if updater.current_report:
                    filename = updater.current_report.get("filename", "Unknown")
                    print(f"📁 Downloaded: {filename}")

                # Update state
                state = load_state()
                state["files"]["excel_files"] = excel_files
                state["report"]["downloaded_at"] = datetime.now().isoformat()
                save_state(state)

                update_step_status(
                    "download",
                    "success",
                    execution_time,
                    files_downloaded=excel_files,
                    download_count=len(excel_files),
                )
            else:
                print(
                    f"⚠️ No files downloaded - may already be current ({format_duration(execution_time)})"
                )
                update_step_status(
                    "download", "success", execution_time, download_count=0
                )

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Download failed: {error_msg}")
            update_step_status("download", "failed", error=error_msg)
            sys.exit(1)

    def _run_convert_step(updater: Any) -> None:
        """Run step 3: Convert Excel to CSV format."""
        update_step_status("convert", "running")

        def _convert() -> Any:
            # Check if Excel files are available (either from current run or previous)
            data_dir = Path("data")
            excel_files = list(data_dir.glob("*.xlsx"))

            if not excel_files:
                # Try to get from state
                state = load_state()
                if not state["files"]["excel_files"]:
                    raise Exception(
                        "No Excel files found - please run download step first"
                    )

            return updater.convert_excel_to_csv()

        try:
            convert_success, execution_time = execute_and_time(_convert)

            if convert_success:
                print(
                    f"✅ Excel to CSV conversion completed successfully ({format_duration(execution_time)})"
                )

                # Find converted CSV files
                data_dir = Path("data")
                csv_files = [f.name for f in data_dir.glob("*.csv")]

                print("📄 Generated CSV files:")
                for csv_file in csv_files:
                    print(f"  📄 {csv_file}")

                # Update state
                state = load_state()
                state["files"]["csv_files"] = csv_files
                save_state(state)

                update_step_status(
                    "convert",
                    "success",
                    execution_time,
                    files_converted=csv_files,
                    convert_count=len(csv_files),
                )
            else:
                error_msg = "Excel to CSV conversion failed"
                print(f"❌ {error_msg}")
                update_step_status("convert", "failed", error=error_msg)
                sys.exit(1)

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Convert failed: {error_msg}")
            update_step_status("convert", "failed", error=error_msg)
            sys.exit(1)

    def _run_import_step(updater: Any) -> None:
        """Run step 4: Import CSV data to database."""
        update_step_status("import", "running")

        def _import() -> Any:
            return updater.import_csv_to_database(clear_existing=True)

        try:
            import_success, execution_time = execute_and_time(_import)

            if import_success:
                # Try to get import statistics (this depends on updater implementation)
                companies_imported = 0
                if hasattr(updater, "last_import_stats"):
                    companies_imported = updater.last_import_stats.get(
                        "total_companies", 0
                    )

                print(
                    f"✅ Database import completed successfully ({format_duration(execution_time)})"
                )
                print(f"📊 Imported {companies_imported} companies")

                update_step_status(
                    "import",
                    "success",
                    execution_time,
                    companies_imported=companies_imported,
                )
            else:
                error_msg = "Database import failed"
                print(f"❌ {error_msg}")
                update_step_status("import", "failed", error=error_msg)
                sys.exit(1)

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Import failed: {error_msg}")
            update_step_status("import", "failed", error=error_msg)
            sys.exit(1)

    def _run_company_update_step() -> None:
        """Run step 5: Update companies in database."""
        update_step_status("company_update", "running")

        def _company_update() -> str:
            # Run the company updater script
            result = subprocess.run(
                [sys.executable, ".github/scripts/company_updater.py"],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result.stdout

        try:
            output, execution_time = execute_and_time(_company_update)

            # Parse statistics from output
            companies_processed = 0
            companies_updated = 0
            companies_new = 0

            # Extract numbers from output using regex
            if "companies processed" in output:
                match = re.search(r"(\d+)\s+companies processed", output)
                if match:
                    companies_processed = int(match.group(1))

            if "companies updated" in output:
                match = re.search(r"(\d+)\s+companies updated", output)
                if match:
                    companies_updated = int(match.group(1))

            if "new companies" in output:
                match = re.search(r"(\d+)\s+new companies", output)
                if match:
                    companies_new = int(match.group(1))

            print(
                f"✅ Company update completed successfully ({format_duration(execution_time)})"
            )
            print(
                f"📊 Processed: {companies_processed}, Updated: {companies_updated}, New: {companies_new}"
            )

            update_step_status(
                "company_update",
                "success",
                execution_time,
                companies_processed=companies_processed,
                companies_updated=companies_updated,
                companies_new=companies_new,
            )

        except subprocess.TimeoutExpired:
            error_msg = "Company update timed out after 5 minutes"
            print(f"❌ {error_msg}")
            update_step_status("company_update", "failed", error=error_msg)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            error_msg = f"Company update script failed (exit code: {e.returncode})"
            print(f"❌ {error_msg}")
            if e.stdout:
                print(f"📋 Output: {e.stdout}")
            if e.stderr:
                print(f"🚨 Error: {e.stderr}")
            update_step_status("company_update", "failed", error=error_msg)
            sys.exit(1)
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Company update failed: {error_msg}")
            update_step_status("company_update", "failed", error=error_msg)
            sys.exit(1)

    def _run_quota_update_step() -> None:
        """Run step 6: Update quota records."""
        update_step_status("quota_update", "running")

        def _quota_update() -> str:
            # Run the quota updater script
            result = subprocess.run(
                [sys.executable, ".github/scripts/quota_updater.py"],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result.stdout

        try:
            output, execution_time = execute_and_time(_quota_update)

            # Parse quota statistics from output
            quotas_total = 0

            # Extract quota count from output
            if "quota records" in output:
                match = re.search(r"(\d+)\s+quota records", output)
                if match:
                    quotas_total = int(match.group(1))

            print(
                f"✅ Quota update completed successfully ({format_duration(execution_time)})"
            )
            print(f"📊 Total quota records: {quotas_total}")

            update_step_status(
                "quota_update", "success", execution_time, quotas_total=quotas_total
            )

        except subprocess.TimeoutExpired:
            error_msg = "Quota update timed out after 5 minutes"
            print(f"❌ {error_msg}")
            update_step_status("quota_update", "failed", error=error_msg)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            error_msg = f"Quota update script failed (exit code: {e.returncode})"
            print(f"❌ {error_msg}")
            if e.stdout:
                print(f"📋 Output: {e.stdout}")
            if e.stderr:
                print(f"🚨 Error: {e.stderr}")
            update_step_status("quota_update", "failed", error=error_msg)
            sys.exit(1)
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Quota update failed: {error_msg}")
            update_step_status("quota_update", "failed", error=error_msg)
            sys.exit(1)


if __name__ == "__main__":
    main()
