/**
 * BDEW Admin Dashboard JavaScript
 * AlpineJS implementation for reactive dashboard functionality
 */

function dashboard() {
  return {
    stats: {},
    companies: [],
    codes: [],
    functions: [],
    activeTab: "companies",
    showModal: false,
    selectedCompany: null,
    companyDetails: null,

    init() {
      console.log("Dashboard initialisiert");
      this.loadStats();
      this.loadCompanies();
    },

    async loadStats() {
      try {
        const response = await fetch("/api/dashboard/stats");
        this.stats = await response.json();
      } catch (error) {
        console.error("Error loading stats:", error);
      }
    },

    async loadCompanies() {
      try {
        const response = await fetch("/api/companies");
        this.companies = await response.json();
      } catch (error) {
        console.error("Error loading companies:", error);
      }
    },

    async loadCodes() {
      try {
        const response = await fetch("/api/bdew-codes");
        this.codes = await response.json();
      } catch (error) {
        console.error("Error loading codes:", error);
      }
    },

    async loadFunctions() {
      try {
        const response = await fetch("/api/market-functions");
        this.functions = await response.json();
      } catch (error) {
        console.error("Error loading functions:", error);
      }
    },

    async showCompanyDetails(companyName) {
      console.log("Lade Details für:", companyName);
      try {
        const response = await fetch(`/api/companies/${encodeURIComponent(companyName)}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        this.companyDetails = await response.json();
        console.log("Company Details:", this.companyDetails);
        this.selectedCompany = companyName;
        this.showModal = true;
      } catch (error) {
        console.error("Error loading company details:", error);
        alert("Fehler beim Laden der Unternehmensdetails: " + error.message);
      }
    },

    closeModal() {
      this.showModal = false;
      this.selectedCompany = null;
      this.companyDetails = null;
    },

    showTab(tabName) {
      console.log("Switching to tab:", tabName);
      this.activeTab = tabName;

      // Load data if needed
      if (tabName === "codes" && this.codes.length === 0) {
        this.loadCodes();
      } else if (tabName === "functions" && this.functions.length === 0) {
        this.loadFunctions();
      }
    },
  };
}
