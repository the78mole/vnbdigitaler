/**
 * VNB Digitaler Admin Dashboard
 * CoreUI + DataTables Integration
 */

class AdminDashboard {
  constructor() {
    this.dataTablesConfig = {
      language: {
        url: "/static/js/datatables-de.json",
      },
      pageLength: 25,
      lengthMenu: [
        [10, 25, 50, 100, -1],
        [10, 25, 50, 100, "Alle"],
      ],
      responsive: true,
      processing: true,
      serverSide: true,
      dom:
        '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
        '<"row"<"col-sm-12"B>>' +
        '<"row"<"col-sm-12"tr>>' +
        '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
      buttons: [
        {
          extend: "excel",
          text: '<i class="cil-cloud-download"></i> Excel',
          className: "btn btn-outline-success btn-sm",
        },
        {
          extend: "csv",
          text: '<i class="cil-cloud-download"></i> CSV',
          className: "btn btn-outline-info btn-sm",
        },
        {
          text: '<i class="cil-reload"></i> Aktualisieren',
          className: "btn btn-outline-primary btn-sm",
          action: function (e, dt, node, config) {
            dt.ajax.reload();
          },
        },
      ],
    };

    this.currentTable = null;
    this.init();
  }

  init() {
    this.setupNavigation();
    this.loadDashboardStats();
    this.showTab("dashboard");
  }

  setupNavigation() {
    document.querySelectorAll("[data-tab]").forEach(link => {
      link.addEventListener("click", e => {
        e.preventDefault();
        const tabName = e.currentTarget.getAttribute("data-tab");
        this.showTab(tabName);

        document.querySelectorAll(".nav-link").forEach(nav => nav.classList.remove("active"));
        e.currentTarget.classList.add("active");
      });
    });

    document.querySelector('a[href="#dashboard"]').addEventListener("click", e => {
      e.preventDefault();
      this.showTab("dashboard");

      document.querySelectorAll(".nav-link").forEach(nav => nav.classList.remove("active"));
      e.currentTarget.classList.add("active");
    });
  }

  showTab(tabName) {
    document.querySelectorAll(".tab-content").forEach(tab => {
      tab.style.display = "none";
      tab.classList.remove("active");
    });

    const targetTab = document.getElementById(`${tabName}-content`);
    if (targetTab) {
      targetTab.style.display = "block";
      targetTab.classList.add("active");
    }

    if (this.currentTable) {
      this.currentTable.destroy();
      this.currentTable = null;
    }

    switch (tabName) {
      case "bdew-codes":
        this.initBdewCodesTable();
        break;
      case "companies":
        this.initCompaniesTable();
        break;
      case "functions":
        this.initFunctionsTable();
        break;
      case "dashboard":
        this.loadDashboardStats();
        break;
    }
  }

  showLoading() {
    document.getElementById("loading-overlay").classList.remove("d-none");
  }

  hideLoading() {
    document.getElementById("loading-overlay").classList.add("d-none");
  }

  async apiCall(url, options = {}) {
    try {
      this.showLoading();
      const response = await fetch(url, {
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("API call failed:", error);
      this.showError("Fehler beim Laden der Daten: " + error.message);
      throw error;
    } finally {
      this.hideLoading();
    }
  }

  showError(message) {
    const toast = document.createElement("div");
    toast.className = "toast position-fixed top-0 end-0 m-3";
    toast.style.zIndex = "2100";
    toast.innerHTML = `
            <div class="toast-header bg-danger text-white">
                <i class="cil-warning me-2"></i>
                <strong class="me-auto">Fehler</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;

    document.body.appendChild(toast);
    const bsToast = new coreui.Toast(toast);
    bsToast.show();

    toast.addEventListener("hidden.bs.toast", () => {
      document.body.removeChild(toast);
    });
  }

  async loadDashboardStats() {
    try {
      const stats = await this.apiCall("/api/dashboard/stats");

      document.getElementById("total-codes").textContent =
        stats.total_codes?.toLocaleString() || "0";
      document.getElementById("total-companies").textContent =
        stats.total_companies?.toLocaleString() || "0";
      document.getElementById("total-functions").textContent =
        stats.total_functions?.toLocaleString() || "0";

      // Format last sync time to human readable
      const lastSyncElement = document.getElementById("last-sync");
      if (lastSyncElement && stats.last_sync) {
        lastSyncElement.textContent = this.formatRelativeTime(stats.last_sync);
      }
    } catch (error) {
      console.error("Failed to load dashboard stats:", error);
    }
  }

  formatRelativeTime(isoString) {
    if (!isoString) return "Unbekannt";

    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return "gerade eben";
    if (diffMins < 60) return `vor ${diffMins} Minute${diffMins === 1 ? "" : "n"}`;
    if (diffHours < 24) return `vor ${diffHours} Stunde${diffHours === 1 ? "" : "n"}`;
    if (diffDays === 1) return "gestern";
    if (diffDays < 7) return `vor ${diffDays} Tagen`;
    if (diffDays < 30)
      return `vor ${Math.floor(diffDays / 7)} Woche${Math.floor(diffDays / 7) === 1 ? "" : "n"}`;
    if (diffDays < 365)
      return `vor ${Math.floor(diffDays / 30)} Monat${Math.floor(diffDays / 30) === 1 ? "" : "en"}`;

    return `vor ${Math.floor(diffDays / 365)} Jahr${Math.floor(diffDays / 365) === 1 ? "" : "en"}`;
  }

  initBdewCodesTable() {
    if (this.currentTable) {
      this.currentTable.destroy();
    }

    this.currentTable = $("#bdew-codes-table").DataTable({
      ...this.dataTablesConfig,
      ajax: {
        url: "/api/bdew-codes",
        type: "GET",
        data: function (d) {
          return {
            page: Math.floor(d.start / d.length) + 1,
            limit: d.length,
            search: d.search.value,
            order_by: d.columns[d.order[0].column].data,
            order_dir: d.order[0].dir,
          };
        },
        dataSrc: function (json) {
          // Set DataTables pagination info correctly
          json.recordsTotal = json.total;
          json.recordsFiltered = json.total;
          json.data = json.items || [];
          return json.data;
        },
      },
      columns: [
        { data: "code", title: "Code" },
        { data: "name", title: "Name" },
        { data: "short_name", title: "Kurzname" },
        { data: "postal_code", title: "PLZ" },
        { data: "city", title: "Ort" },
        {
          data: "market_function_name",
          title: "Marktfunktion",
          render: function (data) {
            return data || '<span class="text-muted">Nicht zugeordnet</span>';
          },
        },
        {
          data: null,
          title: "Aktionen",
          orderable: false,
          className: "table-actions",
          render: function (data, type, row) {
            return `
                            <div class="btn-group btn-group-sm" role="group">
                                <button type="button" class="btn btn-outline-primary" onclick="dashboard.viewDetails('${row.code}')">
                                    <i class="cil-magnifying-glass"></i>
                                </button>
                                <button type="button" class="btn btn-outline-secondary" onclick="dashboard.editItem('${row.code}')">
                                    <i class="cil-pencil"></i>
                                </button>
                            </div>
                        `;
          },
        },
      ],
    });
  }

  initCompaniesTable() {
    if (this.currentTable) {
      this.currentTable.destroy();
    }

    this.currentTable = $("#companies-table").DataTable({
      ...this.dataTablesConfig,
      ajax: {
        url: "/api/companies",
        type: "GET",
        data: function (d) {
          return {
            page: Math.floor(d.start / d.length) + 1,
            limit: d.length,
            search: d.search.value,
          };
        },
        dataSrc: function (json) {
          // Set DataTables pagination info correctly
          json.recordsTotal = json.total;
          json.recordsFiltered = json.total;
          json.data = json.items || [];
          return json.data;
        },
      },
      columns: [
        { data: "name", title: "Name" },
        { data: "short_name", title: "Kurzname" },
        { data: "postal_code", title: "PLZ" },
        { data: "city", title: "Ort" },
        {
          data: "code_count",
          title: "BDEW-Codes",
          render: function (data) {
            return `<span class="badge bg-primary">${data || 0}</span>`;
          },
        },
        {
          data: null,
          title: "Aktionen",
          orderable: false,
          className: "table-actions",
          render: function (data, type, row) {
            return `
                            <div class="btn-group btn-group-sm" role="group">
                                <button type="button" class="btn btn-outline-primary" onclick="dashboard.viewCompanyDetails('${row.id}')">
                                    <i class="cil-magnifying-glass"></i>
                                </button>
                                <button type="button" class="btn btn-outline-secondary" onclick="dashboard.editCompany('${row.id}')">
                                    <i class="cil-pencil"></i>
                                </button>
                            </div>
                        `;
          },
        },
      ],
    });
  }

  initFunctionsTable() {
    if (this.currentTable) {
      this.currentTable.destroy();
    }

    this.currentTable = $("#functions-table").DataTable({
      ...this.dataTablesConfig,
      ajax: {
        url: "/api/functions",
        type: "GET",
        data: function (d) {
          return {
            page: Math.floor(d.start / d.length) + 1,
            limit: d.length,
            search: d.search.value,
          };
        },
        dataSrc: function (json) {
          // Set DataTables pagination info correctly
          json.recordsTotal = json.total;
          json.recordsFiltered = json.total;
          json.data = json.items || [];
          return json.data;
        },
      },
      columns: [
        { data: "code", title: "Code" },
        { data: "name", title: "Bezeichnung" },
        { data: "description", title: "Beschreibung" },
        {
          data: "is_active",
          title: "Aktiv",
          render: function (data) {
            return data
              ? '<span class="badge bg-success">Aktiv</span>'
              : '<span class="badge bg-secondary">Inaktiv</span>';
          },
        },
        {
          data: null,
          title: "Aktionen",
          orderable: false,
          className: "table-actions",
          render: function (data, type, row) {
            return `
                            <div class="btn-group btn-group-sm" role="group">
                                <button type="button" class="btn btn-outline-secondary" onclick="dashboard.editFunction('${row.code}')">
                                    <i class="cil-pencil"></i>
                                </button>
                            </div>
                        `;
          },
        },
      ],
    });
  }

  viewDetails(code) {
    console.log("View details for code:", code);
  }

  editItem(code) {
    console.log("Edit item with code:", code);
  }

  viewCompanyDetails(id) {
    console.log("View company details for ID:", id);
  }

  editCompany(id) {
    console.log("Edit company with ID:", id);
  }

  editFunction(code) {
    console.log("Edit function with code:", code);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  window.dashboard = new AdminDashboard();

  const sidebar = document.querySelector(".sidebar");
  if (sidebar) {
    new coreui.Sidebar(sidebar);
  }

  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-coreui-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new coreui.Tooltip(tooltipTriggerEl);
  });
});
