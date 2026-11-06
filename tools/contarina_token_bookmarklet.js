(async function () {
  const domain = "sol.servizicontarina.it";
  if (window.location.protocol !== "https:" || window.location.hostname !== domain) {
    window.alert("Apri prima https://sol.servizicontarina.it/ e accedi al tuo account.");
    return;
  }

  const item = document.cookie.split(";").map((value) => value.trim())
    .find((value) => value.startsWith("accessToken="));
  if (!item) {
    window.alert("Cookie accessToken non disponibile. Esegui il login su SOL e riprova.");
    return;
  }

  let token;
  try {
    token = decodeURIComponent(item.slice("accessToken=".length));
  } catch {
    window.alert("Il cookie accessToken non puo essere decodificato.");
    return;
  }

  const parts = token.split(".");
  if (parts.length !== 3 || !parts.every((part) => /^[A-Za-z0-9_-]+$/.test(part))) {
    window.alert("Il cookie non contiene un JWT nel formato previsto.");
    return;
  }

  let expiry;
  try {
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(payload.padEnd(Math.ceil(payload.length / 4) * 4, "="));
    const claims = JSON.parse(new TextDecoder().decode(Uint8Array.from(decoded, (c) => c.charCodeAt(0))));
    expiry = claims.exp;
  } catch {
    window.alert("Non riesco a leggere la scadenza del JWT.");
    return;
  }

  const remaining = Math.floor((expiry * 1000 - Date.now()) / 60000);
  if (!Number.isFinite(expiry) || remaining < 2) {
    window.alert("Sessione SOL scaduta o quasi scaduta: esegui un nuovo login.");
    return;
  }

  try {
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      throw new Error("Clipboard API not available");
    }
    await navigator.clipboard.writeText(token);
    window.alert(`Token copiato negli appunti (valido per circa ${remaining} minuti). Incollalo solo nella configurazione di Home Assistant.`);
  } catch {
    window.prompt("Il browser non consente la copia automatica. Copia il token solo nella configurazione di Home Assistant:", token);
  }
})();