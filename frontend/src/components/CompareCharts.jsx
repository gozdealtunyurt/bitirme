// src/components/CompareCharts.jsx
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import { KATEGORI_LABELS } from "../constants/config";
import { getScoreColor } from "../utils/scoreUtils";
import "./CompareCharts.css";

function CompareCharts({ data1, data2, mahalle1, mahalle2 }) {
  // dataKey sabit ("skor1"/"skor2"), isim mahalle adı — aynı isimli mahalleler çakışmaz
  const chartData = Object.keys(KATEGORI_LABELS).map(kat => ({
    kategori: KATEGORI_LABELS[kat],
    skor1: data1.skorlar[kat],
    skor2: data2.skorlar[kat],
  }));

  const detailData = Object.keys(KATEGORI_LABELS).map(kat => ({
    kategori: KATEGORI_LABELS[kat],
    key: kat,
    skor1: data1.skorlar[kat],
    skor2: data2.skorlar[kat],
    count1: data1.counts[kat],
    count2: data2.counts[kat],
  }));

  const tooltipStyle = {
    background: "#ffffff",
    border: "1px solid #dfe8e2",
    borderRadius: 6,
    color: "#172033",
    fontSize: 13,
    boxShadow: "0 10px 24px rgba(29,58,43,0.12)",
  };

  return (
    <div className="charts-section">
      {/* Radar Chart */}
      <div className="chart-container">
        <h4 className="chart-title">Radar Karşılaştırması</h4>
        <ResponsiveContainer width="100%" height={320}>
          <RadarChart data={chartData}>
            <PolarGrid stroke="#dfe8e2" />
            <PolarAngleAxis
              dataKey="kategori"
              tick={{ fill: "#526059", fontSize: 12, fontWeight: 700 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: "#89948d", fontSize: 10 }}
            />
            <Radar
              name={mahalle1}
              dataKey="skor1"
              stroke="#176b5b"
              fill="#176b5b"
              fillOpacity={0.2}
              strokeWidth={2}
            />
            <Radar
              name={mahalle2}
              dataKey="skor2"
              stroke="#d8862f"
              fill="#d8862f"
              fillOpacity={0.2}
              strokeWidth={2}
            />
            <Legend wrapperStyle={{ color: "#526059", fontSize: 12, fontWeight: 700 }} />
            <Tooltip contentStyle={tooltipStyle} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Bar Chart */}
      <div className="chart-container">
        <h4 className="chart-title">Kategori Karşılaştırması</h4>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6eee8" />
            <XAxis
              dataKey="kategori"
              tick={{ fill: "#526059", fontSize: 11, fontWeight: 700 }}
              axisLine={{ stroke: "#dfe8e2" }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: "#89948d", fontSize: 11 }}
              axisLine={{ stroke: "#dfe8e2" }}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ color: "#526059", fontSize: 12, fontWeight: 700 }} />
            <Bar dataKey="skor1" name={mahalle1} fill="#176b5b" radius={[4, 4, 0, 0]} />
            <Bar dataKey="skor2" name={mahalle2} fill="#d8862f" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detay Tablosu */}
      <div className="detail-table-container">
        <h4 className="chart-title">Detay Tablosu</h4>
        <table className="detail-table">
          <thead>
            <tr>
              <th>Kategori</th>
              <th>{mahalle1}</th>
              <th>{mahalle2}</th>
              <th>Sonuç</th>
            </tr>
          </thead>
          <tbody>
            {detailData.map(row => {
              const diff = row.skor1 - row.skor2;
              const winner = diff > 0 ? mahalle1 : diff < 0 ? mahalle2 : "Eşit";
              return (
                <tr key={row.key}>
                  <td className="td-kategori">{row.kategori}</td>
                  <td>
                    <span className="td-skor" style={{ color: getScoreColor(row.skor1) }}>
                      {row.skor1}
                    </span>
                    <span className="td-count">({row.count1} yer)</span>
                  </td>
                  <td>
                    <span className="td-skor" style={{ color: getScoreColor(row.skor2) }}>
                      {row.skor2}
                    </span>
                    <span className="td-count">({row.count2} yer)</span>
                  </td>
                  <td className="td-winner">
                    {diff === 0 ? "Eşit" : `${winner} (+${Math.abs(diff)})`}
                  </td>
                </tr>
              );
            })}
            <tr className="total-row">
              <td className="td-kategori">Genel Toplam</td>
              <td>
                <span className="td-skor td-total" style={{ color: getScoreColor(data1.toplam_skor) }}>
                  {data1.toplam_skor}
                </span>
              </td>
              <td>
                <span className="td-skor td-total" style={{ color: getScoreColor(data2.toplam_skor) }}>
                  {data2.toplam_skor}
                </span>
              </td>
              <td className="td-winner td-total">
                {data1.toplam_skor === data2.toplam_skor
                  ? "Eşit"
                  : data1.toplam_skor > data2.toplam_skor
                    ? `${mahalle1} (+${data1.toplam_skor - data2.toplam_skor})`
                    : `${mahalle2} (+${data2.toplam_skor - data1.toplam_skor})`}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default CompareCharts;
