// src/services/locationService.js
// Primary kaynak: local JSON. Dropdown'lar hızlı açılsın diye önce bu veri kullanılır.
import locationData from "../data/il_ilce_mahalle.json";

const TR_LOWER = {
  A: "a",
  B: "b",
  C: "c",
  Ç: "ç",
  D: "d",
  E: "e",
  F: "f",
  G: "g",
  Ğ: "ğ",
  H: "h",
  I: "ı",
  İ: "i",
  J: "j",
  K: "k",
  L: "l",
  M: "m",
  N: "n",
  O: "o",
  Ö: "ö",
  P: "p",
  R: "r",
  S: "s",
  Ş: "ş",
  T: "t",
  U: "u",
  Ü: "ü",
  V: "v",
  Y: "y",
  Z: "z",
};

const TR_UPPER = Object.fromEntries(
  Object.entries(TR_LOWER).map(([upper, lower]) => [lower, upper])
);

function trLower(str) {
  return String(str)
    .split("")
    .map((char) => TR_LOWER[char] ?? char.toLocaleLowerCase("tr-TR"))
    .join("");
}

function trTitle(str) {
  return String(str)
    .split(" ")
    .map((word) => {
      if (!word) return word;
      const first = trLower(word[0]);
      return (TR_UPPER[first] ?? first.toLocaleUpperCase("tr-TR")) + trLower(word.slice(1));
    })
    .join(" ");
}

function formatDisplay(name) {
  return trTitle(name);
}

function norm(value) {
  return trLower(String(value || "").trim())
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function findKey(mapping, name) {
  const target = norm(name);
  return Object.keys(mapping).find((key) => norm(key) === target) ?? null;
}

export function getSehirler() {
  return Object.keys(locationData)
    .map(formatDisplay)
    .sort((a, b) => a.localeCompare(b, "tr"));
}

export function getIlceler(sehirAdi) {
  const sehirKey = findKey(locationData, sehirAdi);
  if (!sehirKey) return [];
  return Object.keys(locationData[sehirKey])
    .map(formatDisplay)
    .sort((a, b) => a.localeCompare(b, "tr"));
}

export function getMahalleler(sehirAdi, ilceAdi) {
  const sehirKey = findKey(locationData, sehirAdi);
  if (!sehirKey) return [];
  const ilceKey = findKey(locationData[sehirKey], ilceAdi);
  if (!ilceKey) return [];

  const seen = new Set();
  const result = [];
  for (const mahalle of locationData[sehirKey][ilceKey]) {
    const display = formatDisplay(mahalle);
    if (!seen.has(display)) {
      seen.add(display);
      result.push(display);
    }
  }

  return result.sort((a, b) => a.localeCompare(b, "tr"));
}
