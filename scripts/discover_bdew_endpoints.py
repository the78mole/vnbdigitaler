#!/usr/bin/env python3
"""
BDEW Endpoint Discovery Tool.

Analysiert die BDEW-Website um alle verfügbaren API-Endpunkte
und Marktteilnehmer-Kategorien zu identifizieren.
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urljoin

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"❌ Required packages: {e}")
    print("Run: uv add httpx beautifulsoup4")
    sys.exit(1)

# Constants
CONTENT_PREVIEW_LENGTH = 200
MIN_LIST_ITEMS = 2
MAX_RECOMMENDATIONS = 3
HTTP_OK = 200


class BDEWEndpointDiscovery:
    """
    Discovers all available BDEW API endpoints and market participant categories.

    Systematically analyzes the BDEW website structure to find:
    - All available data categories
    - API endpoints for different market participants
    - Data structures and parameters
    - Available roles and classifications
    """

    BASE_URL = "https://bdew-codes.de"
    START_URLS: ClassVar[list[str]] = [
        "https://bdew-codes.de/Codenumbers/BDEWCodes/CodeOverview",
        "https://bdew-codes.de/Codenumbers/BDEWCodes",
        "https://bdew-codes.de/Codenumbers/ElectricityGridOperatorCodes",
        "https://bdew-codes.de/Codenumbers/NetLocationId",
        "https://bdew-codes.de/Codenumbers/NetAreaId",
        "https://bdew-codes.de/Codenumbers/EMobilityId",
        "https://bdew-codes.de/Codenumbers/EnergyIdentificationCode",
    ]

    def __init__(self, output_dir: Path | None = None, verbose: bool = False):
        self.output_dir = output_dir or Path("tmp/bdew_discovery")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.verbose = verbose
        self.logger = self._setup_logging()

        self.discovered_endpoints = {}
        self.discovered_categories = {}
        self.discovered_parameters = {}
        self.visited_urls: set[str] = set()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return logging.getLogger(__name__)

    async def discover_all_endpoints(self) -> dict[str, Any]:
        """
        Main discovery method - analyzes entire BDEW website structure.

        Returns:
            Comprehensive structure of all discovered endpoints and categories
        """
        self.logger.info("🔍 Starting BDEW endpoint discovery...")

        async with httpx.AsyncClient(
            headers={
                "User-Agent": "vnbdigitaler/1.0 (BDEW Discovery Tool; +https://github.com/the78mole/vnbdigitaler)"
            },
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            self.client = client

            # 1. Analyze main pages
            for url in self.START_URLS:
                await self._analyze_page(url)

            # 2. Discover API endpoints
            await self._discover_api_endpoints()

            # 3. Analyze data structures
            await self._analyze_data_structures()

            # 4. Generate comprehensive report
            discovery_results = self._generate_discovery_report()

            # 5. Save results
            await self._save_discovery_results(discovery_results)

            return discovery_results

    async def _analyze_page(self, url: str) -> None:
        """Analyze a single page for endpoints and structure."""
        if url in self.visited_urls:
            return

        self.logger.debug(f"Analyzing page: {url}")
        self.visited_urls.add(url)

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract navigation links
            nav_links = self._extract_navigation_links(soup, url)

            # Look for API endpoints
            api_endpoints = self._extract_api_endpoints(soup, url)

            # Analyze JavaScript for AJAX calls
            js_endpoints = self._extract_js_endpoints(soup, url)

            # Look for data tables and structures
            data_structures = self._extract_data_structures(soup, url)

            # Store findings
            page_analysis = {
                "url": url,
                "title": self._extract_page_title(soup),
                "nav_links": nav_links,
                "api_endpoints": api_endpoints,
                "js_endpoints": js_endpoints,
                "data_structures": data_structures,
                "forms": self._extract_forms(soup),
            }

            self.discovered_categories[url] = page_analysis

            # Follow relevant links
            for link in nav_links:
                if self._is_relevant_link(link):
                    await self._analyze_page(link)

        except Exception as e:
            self.logger.error(f"Error analyzing {url}: {e}")

    def _extract_navigation_links(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[str]:
        """Extract navigation links from page."""
        links = []

        # Main navigation
        nav_elements = soup.find_all(
            ["nav", "ul"], class_=re.compile(r"nav|menu", re.I)
        )

        for nav in nav_elements:
            for link in nav.find_all("a", href=True):
                full_url = urljoin(base_url, link["href"])
                if self._is_bdew_url(full_url):
                    links.append(full_url)

        # Sidebar links
        sidebar_links = soup.find_all("a", href=re.compile(r"/Codenumbers/", re.I))
        for link in sidebar_links:
            full_url = urljoin(base_url, link["href"])
            links.append(full_url)

        return list(set(links))

    def _extract_api_endpoints(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract API endpoints from page."""
        endpoints = []

        # Look for form actions (common for AJAX endpoints)
        forms = soup.find_all("form")
        for form in forms:
            action = form.get("action")
            if action:
                endpoint_url = urljoin(base_url, action)
                method = form.get("method", "GET").upper()

                # Analyze form inputs
                inputs = []
                for input_elem in form.find_all(["input", "select", "textarea"]):
                    input_info = {
                        "name": input_elem.get("name"),
                        "type": input_elem.get("type", "text"),
                        "value": input_elem.get("value"),
                        "required": input_elem.has_attr("required"),
                    }
                    inputs.append(input_info)

                endpoints.append(
                    {
                        "url": endpoint_url,
                        "method": method,
                        "type": "form",
                        "inputs": inputs,
                    }
                )

        return endpoints

    def _extract_js_endpoints(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract AJAX endpoints from JavaScript code."""
        endpoints = []

        # Find all script tags
        scripts = soup.find_all("script")

        for script in scripts:
            if script.string:
                # Look for AJAX URLs
                ajax_patterns = [
                    r'url\s*:\s*["\']([^"\']*)["\']',
                    r'\.ajax\s*\(\s*["\']([^"\']*)["\']',
                    r'\.post\s*\(\s*["\']([^"\']*)["\']',
                    r'\.get\s*\(\s*["\']([^"\']*)["\']',
                ]

                for pattern in ajax_patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE)
                    for match in matches:
                        if match.startswith("/") or "bdew-codes.de" in match:
                            endpoint_url = urljoin(base_url, match)
                            endpoints.append(
                                {
                                    "url": endpoint_url,
                                    "type": "ajax",
                                    "source": "javascript",
                                    "context": (
                                        script.string[:CONTENT_PREVIEW_LENGTH] + "..."
                                        if len(script.string) > CONTENT_PREVIEW_LENGTH
                                        else script.string
                                    ),
                                }
                            )

        return endpoints

    def _extract_data_structures(
        self, soup: BeautifulSoup, _url: str
    ) -> dict[str, Any]:
        """Analyze data structures on the page."""
        structures = {
            "tables": [],
            "lists": [],
            "forms": [],
        }

        # Analyze tables
        tables = soup.find_all("table")
        for table in tables:
            headers = [th.get_text().strip() for th in table.find_all(["th", "td"])]
            if headers:
                structures["tables"].append(
                    {
                        "headers": headers[:10],  # First 10 headers
                        "row_count": len(table.find_all("tr")) - 1,  # Minus header row
                    }
                )

        # Analyze lists
        lists = soup.find_all(["ul", "ol"])
        for list_elem in lists:
            items = [li.get_text().strip() for li in list_elem.find_all("li")]
            if len(items) > MIN_LIST_ITEMS:  # Only meaningful lists
                structures["lists"].append(
                    {
                        "items": items[:10],  # First 10 items
                        "total_items": len(items),
                    }
                )

        return structures

    def _extract_forms(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract form information."""
        forms = []

        for form in soup.find_all("form"):
            form_info = {
                "action": form.get("action"),
                "method": form.get("method", "GET"),
                "inputs": [],
            }

            for input_elem in form.find_all(["input", "select", "textarea"]):
                input_info = {
                    "name": input_elem.get("name"),
                    "type": input_elem.get("type", "text"),
                    "placeholder": input_elem.get("placeholder"),
                    "required": input_elem.has_attr("required"),
                }

                # For select elements, get options
                if input_elem.name == "select":
                    options = [
                        opt.get("value") for opt in input_elem.find_all("option")
                    ]
                    input_info["options"] = options

                form_info["inputs"].append(input_info)

            forms.append(form_info)

        return forms

    def _extract_page_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_elem = soup.find("title")
        if title_elem:
            return title_elem.get_text().strip()

        h1_elem = soup.find("h1")
        if h1_elem:
            return h1_elem.get_text().strip()

        return "Unknown"

    def _is_relevant_link(self, url: str) -> bool:
        """Check if a link is relevant for discovery."""
        relevant_patterns = [
            r"/Codenumbers/",
            r"/BDEWCodes/",
            r"/ElectricityGrid/",
            r"/Gas/",
            r"/Energy/",
        ]

        return any(
            re.search(pattern, url, re.IGNORECASE) for pattern in relevant_patterns
        )

    def _is_bdew_url(self, url: str) -> bool:
        """Check if URL belongs to BDEW domain."""
        return "bdew-codes.de" in url

    async def _discover_api_endpoints(self) -> None:
        """Discover actual API endpoints by testing common patterns."""
        self.logger.info("🔍 Discovering API endpoints...")

        # Known endpoint patterns
        endpoint_patterns = [
            "/Codenumbers/ElectricityGridOperatorCodes/GetElectricityList",
            "/Codenumbers/GasGridOperatorCodes/GetGasList",
            "/Codenumbers/BDEWCodes/GetMarketParticipants",
            "/Codenumbers/BDEWCodes/GetBDEWList",
            "/Codenumbers/NetLocationId/GetNetLocationList",
            "/Codenumbers/NetAreaId/GetNetAreaList",
            "/Codenumbers/EMobilityId/GetEMobilityList",
            "/Codenumbers/EnergyIdentificationCode/GetEICList",
        ]

        for pattern in endpoint_patterns:
            endpoint_url = self.BASE_URL + pattern
            await self._test_endpoint(endpoint_url)

    async def _test_endpoint(self, endpoint_url: str) -> None:
        """Test if an endpoint exists and what parameters it accepts."""
        self.logger.debug(f"Testing endpoint: {endpoint_url}")

        try:
            # Test with minimal parameters
            test_params = {
                "jtStartIndex": 0,
                "jtPageSize": 1,
                "jtSorting": "Number ASC",
            }

            response = await self.client.post(
                endpoint_url,
                data=test_params,
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
            )

            if response.status_code == HTTP_OK:
                try:
                    data = response.json()
                    self.discovered_endpoints[endpoint_url] = {
                        "status": "active",
                        "response_structure": self._analyze_response_structure(data),
                        "test_response": data,
                    }
                    self.logger.info(f"✅ Active endpoint found: {endpoint_url}")
                except (json.JSONDecodeError, ValueError) as e:
                    self.discovered_endpoints[endpoint_url] = {
                        "status": "active_non_json",
                        "content_type": response.headers.get("content-type"),
                        "parse_error": str(e),
                    }
            else:
                self.discovered_endpoints[endpoint_url] = {
                    "status": f"error_{response.status_code}",
                }

        except Exception as e:
            self.discovered_endpoints[endpoint_url] = {
                "status": "connection_error",
                "error": str(e),
            }

    def _analyze_response_structure(self, data: Any) -> dict[str, Any]:
        """Analyze the structure of API response."""
        if isinstance(data, dict):
            structure = {
                "type": "object",
                "keys": list(data.keys()),
            }

            # Analyze Records if present
            if (
                "Records" in data
                and isinstance(data["Records"], list)
                and data["Records"]
            ):
                sample_record = data["Records"][0]
                structure["record_structure"] = {
                    "type": "array_of_objects",
                    "sample_keys": (
                        list(sample_record.keys())
                        if isinstance(sample_record, dict)
                        else None
                    ),
                    "record_count": len(data["Records"]),
                }

            return structure

        return {"type": type(data).__name__}

    async def _analyze_data_structures(self) -> None:
        """Analyze data structures from active endpoints."""
        self.logger.info("📊 Analyzing data structures...")

        for endpoint_url, endpoint_info in self.discovered_endpoints.items():
            if (
                endpoint_info.get("status") == "active"
                and "test_response" in endpoint_info
            ):
                self.logger.debug(f"Analyzing structure for {endpoint_url}")
                # Additional structure analysis could be done here

    def _generate_discovery_report(self) -> dict[str, Any]:
        """Generate comprehensive discovery report."""
        self.logger.info("📋 Generating discovery report...")

        report = {
            "discovery_summary": {
                "total_pages_analyzed": len(self.discovered_categories),
                "total_endpoints_tested": len(self.discovered_endpoints),
                "active_endpoints": len(
                    [
                        e
                        for e in self.discovered_endpoints.values()
                        if e.get("status") == "active"
                    ]
                ),
                "discovery_date": asyncio.get_event_loop().time(),
            },
            "discovered_categories": self.discovered_categories,
            "discovered_endpoints": self.discovered_endpoints,
            "market_participant_types": self._extract_market_participant_types(),
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _extract_market_participant_types(self) -> list[str]:
        """Extract market participant types from discovered data."""
        types = set()

        # Extract from page titles and content
        for page_info in self.discovered_categories.values():
            title = page_info.get("title", "").lower()

            # Common patterns
            if "stromnetzbetreiber" in title or "electricity" in title:
                types.add("Stromnetzbetreiber")
            if "gasnetzbetreiber" in title or "gas" in title:
                types.add("Gasnetzbetreiber")
            if "lieferant" in title or "supplier" in title:
                types.add("Energielieferant")
            if "messstellenbetreiber" in title or "metering" in title:
                types.add("Messstellenbetreiber")

        return list(types)

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on discovery results."""
        recommendations = []

        active_endpoints = [
            url
            for url, info in self.discovered_endpoints.items()
            if info.get("status") == "active"
        ]

        if len(active_endpoints) > 1:
            recommendations.append(
                "✅ Multiple active endpoints found - implement multi-endpoint data source"
            )

        if any("Gas" in url for url in active_endpoints):
            recommendations.append(
                "🔍 Gas operator endpoints available - extend beyond electricity"
            )

        if any("NetLocation" in url for url in active_endpoints):
            recommendations.append(
                "📍 Network location data available - integrate geographic information"
            )

        recommendations.append("🎯 Implement role-based company classification")
        recommendations.append("🔄 Set up regular discovery to detect new endpoints")

        return recommendations

    async def _save_discovery_results(self, results: dict[str, Any]) -> None:
        """Save discovery results to files."""

        # Save comprehensive results
        results_file = self.output_dir / "bdew_discovery_results.json"
        with results_file.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"💾 Discovery results saved to: {results_file}")

        # Save endpoint summary
        endpoint_summary = {
            "active_endpoints": {
                url: info
                for url, info in self.discovered_endpoints.items()
                if info.get("status") == "active"
            },
            "recommendations": results["recommendations"],
        }

        summary_file = self.output_dir / "endpoint_summary.json"
        with summary_file.open("w", encoding="utf-8") as f:
            json.dump(endpoint_summary, f, indent=2, ensure_ascii=False, default=str)

        # Generate markdown report
        await self._generate_markdown_report(results)

    async def _generate_markdown_report(self, results: dict[str, Any]) -> None:
        """Generate human-readable markdown report."""
        report_file = self.output_dir / "BDEW_DISCOVERY_REPORT.md"

        with report_file.open("w", encoding="utf-8") as f:
            f.write("# BDEW Endpoint Discovery Report\n\n")
            f.write(f"Generated on: {asyncio.get_event_loop().time()}\n\n")

            # Summary
            summary = results["discovery_summary"]
            f.write("## Discovery Summary\n\n")
            f.write(f"- Pages analyzed: {summary['total_pages_analyzed']}\n")
            f.write(f"- Endpoints tested: {summary['total_endpoints_tested']}\n")
            f.write(f"- Active endpoints: {summary['active_endpoints']}\n\n")

            # Active endpoints
            f.write("## Active Endpoints\n\n")
            for url, info in self.discovered_endpoints.items():
                if info.get("status") == "active":
                    f.write(f"### {url}\n")
                    f.write("- Status: ✅ Active\n")
                    if "response_structure" in info:
                        structure = info["response_structure"]
                        f.write(f"- Response type: {structure.get('type')}\n")
                        if "record_structure" in structure:
                            record = structure["record_structure"]
                            f.write(f"- Record count: {record.get('record_count')}\n")
                            if record.get("sample_keys"):
                                f.write(
                                    f"- Sample fields: {', '.join(record['sample_keys'][:5])}\n"
                                )
                    f.write("\n")

            # Recommendations
            f.write("## Recommendations\n\n")
            for rec in results["recommendations"]:
                f.write(f"- {rec}\n")

        self.logger.info(f"📄 Markdown report saved to: {report_file}")


async def main():
    """Main function for standalone execution."""
    parser = argparse.ArgumentParser(
        description="Discover BDEW API endpoints and structure"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tmp/bdew_discovery"),
        help="Output directory for results",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    discovery = BDEWEndpointDiscovery(output_dir=args.output_dir, verbose=args.verbose)

    print("🔍 Starting BDEW Endpoint Discovery...")
    results = await discovery.discover_all_endpoints()

    print("\n📊 Discovery completed!")
    print(f"📁 Results saved to: {args.output_dir}")
    print(
        f"📄 Check {args.output_dir / 'BDEW_DISCOVERY_REPORT.md'} for detailed report"
    )

    # Quick summary
    summary = results["discovery_summary"]
    print("\n✅ Summary:")
    print(f"   Pages analyzed: {summary['total_pages_analyzed']}")
    print(f"   Endpoints tested: {summary['total_endpoints_tested']}")
    print(f"   Active endpoints: {summary['active_endpoints']}")

    if results["recommendations"]:
        print("\n💡 Key recommendations:")
        for rec in results["recommendations"][:MAX_RECOMMENDATIONS]:
            print(f"   {rec}")


if __name__ == "__main__":
    asyncio.run(main())
