const state = {
  rows: [],
  filteredRows: [],
  selectedId: null,
  options: { categoryHints: [], flagHints: [], flagLabels: {} },
};

const elements = {
  list: document.querySelector("#aliasList"),
  rowCount: document.querySelector("#rowCount"),
  statusText: document.querySelector("#statusText"),
  dictionaryPath: document.querySelector("#dictionaryPath"),
  searchInput: document.querySelector("#searchInput"),
  newButton: document.querySelector("#newButton"),
  reloadButton: document.querySelector("#reloadButton"),
  form: document.querySelector("#aliasForm"),
  rowId: document.querySelector("#rowId"),
  canonicalName: document.querySelector("#canonicalName"),
  aliases: document.querySelector("#aliases"),
  relatedNames: document.querySelector("#relatedNames"),
  ticktickListName: document.querySelector("#ticktickListName"),
  categoryHint: document.querySelector("#categoryHint"),
  flagChoices: document.querySelector("#flagChoices"),
  active: document.querySelector("#active"),
  notes: document.querySelector("#notes"),
  deleteButton: document.querySelector("#deleteButton"),
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error((data.errors || ["Request failed"]).join("\n"));
  }
  return data;
}

function setStatus(text) {
  elements.statusText.textContent = text;
}

function semicolonToLines(value) {
  return (value || "").split(";").filter(Boolean).join("\n");
}

function linesToSemicolon(value) {
  return (value || "")
    .split(/\r?\n|;/)
    .map((item) => item.trim())
    .filter(Boolean)
    .join(";");
}

function rowMatches(row, query) {
  if (!query) return true;
  const haystack = [
    row.canonical_name,
    row.aliases,
    row.related_names,
    row.ticktick_list_name,
    row.category_hint,
    row.flags_hint,
    row.notes,
  ].join(" ").toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function renderOptions() {
  elements.categoryHint.innerHTML = "";
  state.options.categoryHints.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value || "(empty)";
    elements.categoryHint.append(option);
  });

  elements.flagChoices.innerHTML = "";
  state.options.flagHints.forEach((flag) => {
    const label = document.createElement("label");
    label.className = "flag-option";
    const translated = state.options.flagLabels[flag] || "";
    const labelText = translated ? `${flag} — ${translated}` : flag;
    label.innerHTML = `<input type="checkbox" value="${flag}"><span>${escapeHtml(labelText)}</span>`;
    elements.flagChoices.append(label);
  });
}

function renderList() {
  const query = elements.searchInput.value.trim();
  state.filteredRows = state.rows.filter((row) => rowMatches(row, query));
  elements.rowCount.textContent = `${state.filteredRows.length} / ${state.rows.length} rows`;
  elements.list.innerHTML = "";

  state.filteredRows.forEach((row) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `alias-item${row.id === state.selectedId ? " active" : ""}`;
    button.innerHTML = `
      <span>
        <span class="alias-name">${escapeHtml(row.canonical_name)}</span>
        <span class="alias-detail">${escapeHtml(row.aliases || "(no aliases)")}</span>
      </span>
      <span class="pill">${escapeHtml(row.ticktick_list_name || "no list")}</span>
    `;
    button.addEventListener("click", () => selectRow(row.id));
    elements.list.append(button);
  });
}

function selectRow(id) {
  state.selectedId = id;
  const row = state.rows.find((item) => item.id === id);
  if (!row) {
    clearForm();
    return;
  }
  elements.rowId.value = row.id;
  elements.canonicalName.value = row.canonical_name;
  elements.aliases.value = semicolonToLines(row.aliases);
  elements.relatedNames.value = semicolonToLines(row.related_names);
  elements.ticktickListName.value = row.ticktick_list_name;
  elements.categoryHint.value = row.category_hint;
  elements.active.checked = row.active !== "false";
  elements.notes.value = row.notes;
  setCheckedFlags(row.flags_hint);
  elements.deleteButton.disabled = false;
  renderList();
}

function clearForm() {
  state.selectedId = null;
  elements.form.reset();
  elements.rowId.value = "";
  elements.active.checked = true;
  setCheckedFlags("");
  elements.deleteButton.disabled = true;
  elements.canonicalName.focus();
  renderList();
}

function selectedFlags() {
  return [...elements.flagChoices.querySelectorAll("input:checked")]
    .map((input) => input.value)
    .join(";");
}

function setCheckedFlags(value) {
  const selected = new Set((value || "").split(";").filter(Boolean));
  elements.flagChoices.querySelectorAll("input").forEach((input) => {
    input.checked = selected.has(input.value);
  });
}

function formPayload() {
  return {
    canonical_name: elements.canonicalName.value,
    aliases: linesToSemicolon(elements.aliases.value),
    related_names: linesToSemicolon(elements.relatedNames.value),
    ticktick_list_name: elements.ticktickListName.value,
    category_hint: elements.categoryHint.value,
    flags_hint: selectedFlags(),
    active: elements.active.checked,
    notes: elements.notes.value,
  };
}

async function loadAll() {
  setStatus("Loading");
  const [options, aliases] = await Promise.all([
    fetchJson("/api/options"),
    fetchJson("/api/aliases"),
  ]);
  state.options = options;
  state.rows = aliases.rows;
  elements.dictionaryPath.textContent = aliases.dictionary;
  renderOptions();
  renderList();
  if (state.rows.length && state.selectedId === null) {
    selectRow(state.rows[0].id);
  }
  setStatus("Ready");
}

async function saveCurrent(event) {
  event.preventDefault();
  const payload = formPayload();
  const id = elements.rowId.value;
  setStatus("Saving");
  try {
    const result = id
      ? await fetchJson(`/api/aliases/${id}`, { method: "PUT", body: JSON.stringify(payload) })
      : await fetchJson("/api/aliases", { method: "POST", body: JSON.stringify(payload) });
    state.rows = result.rows;
    const nextRow = state.rows.find((row) => row.canonical_name === payload.canonical_name);
    state.selectedId = nextRow ? nextRow.id : null;
    renderList();
    selectRow(state.selectedId);
    setStatus(`Saved: ${result.backup}`);
  } catch (error) {
    setStatus(error.message);
  }
}

async function deleteCurrent() {
  const id = elements.rowId.value;
  const name = elements.canonicalName.value;
  if (!id || !window.confirm(`${name} を削除しますか？`)) return;
  setStatus("Deleting");
  try {
    const result = await fetchJson(`/api/aliases/${id}`, { method: "DELETE" });
    state.rows = result.rows;
    clearForm();
    if (state.rows.length) selectRow(state.rows[0].id);
    setStatus(`Deleted: ${result.deleted}`);
  } catch (error) {
    setStatus(error.message);
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

elements.searchInput.addEventListener("input", renderList);
elements.newButton.addEventListener("click", clearForm);
elements.reloadButton.addEventListener("click", loadAll);
elements.form.addEventListener("submit", saveCurrent);
elements.deleteButton.addEventListener("click", deleteCurrent);

loadAll().catch((error) => setStatus(error.message));
