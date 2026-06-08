// src/components/LocationSelector.jsx
import { useState, useEffect } from "react";
import { getSehirler, getIlceler, getMahalleler } from "../services/locationService";
import { API_URL } from "../constants/config";
import "./LocationSelector.css";

export default function LocationSelector({ label, onMahalleSelect }) {
  const [selectedSehir, setSelectedSehir] = useState("");
  const [selectedIlce, setSelectedIlce] = useState("");
  const [selectedMahalle, setSelectedMahalle] = useState("");

  const [sehirler, setSehirler] = useState(() => getSehirler());
  const [ilceler, setIlceler] = useState([]);
  const [mahalleler, setMahalleler] = useState([]);
  const [loading, setLoading] = useState({ sehirler: false, ilceler: false, mahalleler: false });

  // Şehirleri yükle — sayfa açılışında bir kez
  useEffect(() => {
    // API'den de dene (OSM önbellekli data daha güncel olabilir)
    const controller = new AbortController();

    async function loadSehirler() {
      setLoading(l => ({ ...l, sehirler: true }));
      try {
        const response = await fetch(`${API_URL}/api/sehirler`, { signal: controller.signal });
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (data.sehirler?.length) setSehirler(data.sehirler);
      } catch {
        // Hata olursa local JSON zaten hazır.
      } finally {
        setLoading(l => ({ ...l, sehirler: false }));
      }
    }

    loadSehirler();

    return () => controller.abort();
  }, []);

  // İlçeleri yükle
  useEffect(() => {
    if (!selectedSehir) return undefined;

    const controller = new AbortController();

    async function loadIlceler() {
      setLoading(l => ({ ...l, ilceler: true }));
      try {
        const response = await fetch(
          `${API_URL}/api/ilceler/${encodeURIComponent(selectedSehir)}`,
          { signal: controller.signal }
        );
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (data.ilceler?.length) setIlceler(data.ilceler);
      } catch {
        // Local JSON sonucu ekranda kalır.
      } finally {
        setLoading(l => ({ ...l, ilceler: false }));
      }
    }

    loadIlceler();

    return () => controller.abort();
  }, [selectedSehir]);

  // Mahalleleri yükle
  useEffect(() => {
    if (!selectedSehir || !selectedIlce) return undefined;

    const controller = new AbortController();

    async function loadMahalleler() {
      setLoading(l => ({ ...l, mahalleler: true }));
      try {
        const response = await fetch(
          `${API_URL}/api/mahalleler/${encodeURIComponent(selectedSehir)}/${encodeURIComponent(selectedIlce)}`,
          { signal: controller.signal }
        );
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (data.mahalleler?.length) setMahalleler(data.mahalleler);
      } catch {
        // Local JSON sonucu ekranda kalır.
      } finally {
        setLoading(l => ({ ...l, mahalleler: false }));
      }
    }

    loadMahalleler();

    return () => controller.abort();
  }, [selectedSehir, selectedIlce]);

  const handleSehirChange = (e) => {
    const sehir = e.target.value;
    setSelectedSehir(sehir);
    setSelectedIlce("");
    setSelectedMahalle("");
    setIlceler(sehir ? getIlceler(sehir) : []);
    setMahalleler([]);
    onMahalleSelect?.(null);
  };

  const handleIlceChange = (e) => {
    const ilce = e.target.value;
    setSelectedIlce(ilce);
    setSelectedMahalle("");
    setMahalleler(ilce ? getMahalleler(selectedSehir, ilce) : []);
    onMahalleSelect?.(null);
  };

  const handleMahalleChange = (e) => {
    const mahalle = e.target.value;
    setSelectedMahalle(mahalle);
    onMahalleSelect?.(
      mahalle ? { sehir: selectedSehir, ilce: selectedIlce, mahalle } : null
    );
  };

  return (
    <div className="location-selector">
      {label && <h2 className="selector-title">{label}</h2>}

      <div className="dropdown-group">
        <div className="dropdown-wrapper">
          <label>Şehir</label>
          <select value={selectedSehir} onChange={handleSehirChange}>
            <option value="">
              {loading.sehirler ? "Yükleniyor..." : "Şehir seç"}
            </option>
            {sehirler.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="dropdown-wrapper">
          <label>İlçe</label>
          <select
            value={selectedIlce}
            onChange={handleIlceChange}
            disabled={!selectedSehir}
          >
            <option value="">
              {loading.ilceler ? "Yükleniyor..." : !selectedSehir ? "Önce şehir seç" : "İlçe seç"}
            </option>
            {ilceler.map(i => <option key={i} value={i}>{i}</option>)}
          </select>
        </div>

        <div className="dropdown-wrapper">
          <label>Mahalle</label>
          <select
            value={selectedMahalle}
            onChange={handleMahalleChange}
            disabled={!selectedIlce}
          >
            <option value="">
              {loading.mahalleler ? "Yükleniyor..." : !selectedIlce ? "Önce ilçe seç" : "Mahalle seç"}
            </option>
            {mahalleler.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </div>

      {selectedMahalle && (
        <div className="selection-result">
          <span>{selectedSehir}</span>
          <span className="arrow">&gt;</span>
          <span>{selectedIlce}</span>
          <span className="arrow">&gt;</span>
          <span className="highlight">{selectedMahalle}</span>
        </div>
      )}
    </div>
  );
}
