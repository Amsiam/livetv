(function () {
  const DETAILS_PATH = "/admin/catalog/catalogchannel/details/";

  function rowForSelect(select) {
    return (
      select.closest("tr") ||
      select.closest(".form-row") ||
      select.closest(".djn-item") ||
      select.closest("fieldset")
    );
  }

  function setField(row, suffix, value) {
    const input = row.querySelector(`input[name$="-${suffix}"], textarea[name$="-${suffix}"]`);
    if (!input) {
      const byId = document.getElementById(`id_${suffix}`);
      if (byId && row.contains(byId)) {
        byId.value = value || "";
        return;
      }
    }
    if (input) {
      input.value = value || "";
    }
  }

  function hintForRow(row) {
    let hint = row.querySelector(".catalog-source-hint");
    if (!hint) {
      hint = document.createElement("div");
      hint.className = "catalog-source-hint help";
      hint.style.marginTop = "4px";
      const anchor =
        row.querySelector('select[name$="-catalog_channel"]') ||
        row.querySelector('select[name="catalog_channel"]');
      if (anchor && anchor.parentElement) {
        anchor.parentElement.appendChild(hint);
      }
    }
    return hint;
  }

  function setCatalogSelectValue(select, catalogId) {
    if (!catalogId || select.value === catalogId) {
      return;
    }
    if (typeof django !== "undefined" && django.jQuery) {
      django.jQuery(select).val(catalogId);
    } else {
      select.value = catalogId;
    }
  }

  function fillRowFromCatalog(row, select, data) {
    setCatalogSelectValue(select, data.catalog_id);
    setField(row, "name", data.name);
    setField(row, "language", data.language);
    setField(row, "logo_url", data.logo_url);
    setField(row, "stream_url", data.stream_url);

    const hint = hintForRow(row);
    if (data.auto_sources) {
      hint.textContent = `${data.source_count} sources will be available in the app automatically.`;
    } else {
      hint.textContent = "Catalog channel linked. Stream details filled.";
    }
  }

  function fillStandaloneForm(data) {
    const name = document.getElementById("id_name");
    const language = document.getElementById("id_language");
    const logo = document.getElementById("id_logo_url");
    const stream = document.getElementById("id_stream_url");
    if (name) name.value = data.name || "";
    if (language) language.value = data.language || "";
    if (logo) logo.value = data.logo_url || "";
    if (stream) stream.value = data.stream_url || "";

    let hint = document.getElementById("catalog-source-count-hint");
    if (!hint) {
      hint = document.createElement("p");
      hint.id = "catalog-source-count-hint";
      hint.className = "help";
      const catalogField = document.querySelector(".field-catalog_channel");
      if (catalogField) {
        catalogField.appendChild(hint);
      }
    }
    hint.textContent = data.auto_sources
      ? `${data.source_count} sources will be available in the app automatically.`
      : "Catalog channel linked. Stream details filled.";
  }

  function clearCatalogHint(select) {
    const row = rowForSelect(select);
    if (row) {
      const hint = row.querySelector(".catalog-source-hint");
      if (hint) {
        hint.textContent = "";
      }
    }
    const standaloneHint = document.getElementById("catalog-source-count-hint");
    if (standaloneHint) {
      standaloneHint.textContent = "";
    }
  }

  function onCatalogSelected(select) {
    const catalogId = select.value;
    if (!catalogId) {
      clearCatalogHint(select);
      return;
    }

    fetch(`${DETAILS_PATH}${catalogId}/`, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load catalog channel");
        }
        return response.json();
      })
      .then((data) => {
        const row = rowForSelect(select);
        if (row && row.querySelector('input[name$="-stream_url"]')) {
          fillRowFromCatalog(row, select, data);
        } else {
          fillStandaloneForm(data);
        }
      })
      .catch(() => {});
  }

  function bind($) {
    $(document).on(
      "select2:select",
      'select[name$="-catalog_channel"], select[name="catalog_channel"]',
      function () {
        onCatalogSelected(this);
      }
    );

    $(document).on(
      "change",
      'select[name$="-catalog_channel"], select[name="catalog_channel"]',
      function () {
        onCatalogSelected(this);
      }
    );
  }

  function init() {
    if (typeof django === "undefined" || !django.jQuery) {
      return;
    }
    bind(django.jQuery);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
