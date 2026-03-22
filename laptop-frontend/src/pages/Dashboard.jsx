import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDashboard, getInferenceTrace, getCandidates } from '../services/api';
import {
  Activity,
  Filter,
  Cpu,
  CheckCircle,
  X,
  ChevronRight,
  Zap,
  Bot,
  Info,
  Maximize2
} from 'lucide-react';

export default function Dashboard() {
  const { sessionKey } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [trace, setTrace] = useState([]);
  const [selectedLaptop, setSelectedLaptop] = useState(null);
  const [showMatrixModal, setShowMatrixModal] = useState(false);
  const [editablePairwiseMatrix, setEditablePairwiseMatrix] = useState([]);
  const [isEditMatrix, setIsEditMatrix] = useState(false);

  useEffect(() => {
    Promise.all([
      getDashboard(sessionKey),
      getInferenceTrace(sessionKey),
      getCandidates(sessionKey)
    ])
      .then(([dashRes, traceRes]) => {
        setData(dashRes.data);
        setTrace(traceRes.data.trace);
      })
      .catch((err) => console.error("Lỗi khi tải dữ liệu Dashboard", err));
  }, [sessionKey]);

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center px-6">
        <div className="flex items-center gap-3 text-xl md:text-2xl font-bold text-sky-700 animate-pulse">
          <Zap className="animate-bounce" />
          LOADING ANALYSIS DASHBOARD...
        </div>
      </div>
    );
  }

  const matrixLabels = data.ahp?.weights?.map(w => w.name) || [];
  const criteriaCodes = data.ahp?.weights?.map(w => w.criterion) || [];

  const flatMatrix = data.ahp?.pairwiseMatrix || [];
  const criteriaMatrix = [];
  if (flatMatrix.length > 0 && criteriaCodes.length > 0) {
    for (let i = 0; i < criteriaCodes.length; i++) {
      const rowArray = [];
      for (let j = 0; j < criteriaCodes.length; j++) {
        const cell = flatMatrix.find(c => c.row === criteriaCodes[i] && c.col === criteriaCodes[j]);
        rowArray.push(cell ? cell.value : 0);
      }
      criteriaMatrix.push(rowArray);
    }
  }

  const flatNormMatrix = data.ahp?.normalizedMatrix || [];
  const normalizedMatrix = [];
  if (flatNormMatrix.length > 0 && criteriaCodes.length > 0) {
    for (let i = 0; i < criteriaCodes.length; i++) {
      const rowArray = [];
      for (let j = 0; j < criteriaCodes.length; j++) {
        const cell = flatNormMatrix.find(c => c.row === criteriaCodes[i] && c.col === criteriaCodes[j]);
        rowArray.push(cell ? cell.value : 0);
      }
      normalizedMatrix.push(rowArray);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 px-4 py-6 md:px-8 md:py-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* HEADER */}
        <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-8">
          <div className="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-6">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 text-sky-700 px-3 py-1.5 text-xs md:text-sm font-semibold uppercase tracking-wider">
                <Activity size={16} />
                Session ID: {sessionKey.slice(0, 8)}
              </div>

              <div>
                <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900">
                  Analysis Dashboard
                </h1>
                <p className="text-sm md:text-base text-slate-500 mt-2 max-w-3xl">
                  Tổng hợp kết quả lọc, phân tích AHP và gợi ý laptop phù hợp theo nhu cầu của bạn.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 min-w-full xl:min-w-[360px] xl:max-w-[420px]">
              <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs md:text-sm text-slate-500 font-semibold uppercase tracking-wide mb-2">
                  Total Analyzed
                </p>
                <p className="text-2xl md:text-3xl font-extrabold text-sky-700">
                  {data.session?.hardFilterTotalCount ?? 0}
                </p>
              </div>

              <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs md:text-sm text-slate-500 font-semibold uppercase tracking-wide mb-2">
                  Passed Filter
                </p>
                <p className="text-2xl md:text-3xl font-extrabold text-emerald-600">
                  {data.session?.hardFilterPassCount ?? 0}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* AI SUMMARY */}
        {data.aiSuggestion && (
          <section className="bg-gradient-to-r from-sky-600 to-cyan-500 text-white rounded-3xl shadow-sm p-6 md:p-8 relative overflow-hidden">
            <div className="absolute right-0 top-0 w-40 h-40 bg-white/10 rounded-full blur-3xl translate-x-10 -translate-y-10"></div>
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-11 h-11 rounded-2xl bg-white/15 flex items-center justify-center">
                  <Bot size={22} />
                </div>
                <div>
                  <h2 className="text-lg md:text-xl font-bold">Tổng quan chiến lược từ AI</h2>
                  <p className="text-white/80 text-sm md:text-base">Nhận xét chung cho phiên phân tích hiện tại</p>
                </div>
              </div>
              <p className="text-sm md:text-base leading-7 text-white/95 max-w-5xl">
                {data.aiSuggestion}
              </p>
            </div>
          </section>
        )}

        {/* MAIN LAYOUT */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          {/* LEFT + CENTER */}
          <div className="xl:col-span-8 space-y-6">
            {/* STATS + TRACE */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-11 h-11 rounded-2xl bg-sky-100 text-sky-700 flex items-center justify-center">
                    <Filter size={20} />
                  </div>
                  <div>
                    <h3 className="text-lg md:text-xl font-bold text-slate-900">Vòng loại phần cứng</h3>
                    <p className="text-sm text-slate-500">Số máy vượt qua điều kiện ban đầu</p>
                  </div>
                </div>

                <div className="flex items-end gap-3">
                  <span className="text-5xl md:text-6xl font-extrabold text-slate-900">
                    {data.session?.hardFilterPassCount ?? 0}
                  </span>
                  <span className="text-lg md:text-xl text-slate-400 font-semibold mb-2">
                    / {data.session?.hardFilterTotalCount ?? 0}
                  </span>
                </div>

                <div className="mt-5 h-3 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-sky-500 to-cyan-400 rounded-full"
                    style={{
                      width: `${
                        (data.session?.hardFilterTotalCount ?? 0) > 0
                          ? ((data.session?.hardFilterPassCount ?? 0) / (data.session?.hardFilterTotalCount ?? 1)) * 100
                          : 0
                      }%`
                    }}
                  />
                </div>
              </section>

              <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-11 h-11 rounded-2xl bg-amber-100 text-amber-600 flex items-center justify-center">
                    <Activity size={20} />
                  </div>
                  <div>
                    <h3 className="text-lg md:text-xl font-bold text-slate-900">Suy luận AI</h3>
                    <p className="text-sm text-slate-500">Các điểm cộng được áp dụng trong quá trình đánh giá</p>
                  </div>
                </div>

                <div className="space-y-3 max-h-72 overflow-y-auto pr-1 custom-scrollbar">
                  {trace?.filter(t => t.sourceType === 'filter').length > 0 ? (
                    trace.filter(t => t.sourceType === 'filter').map((t, i) => (
                      <div
                        key={i}
                        className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                      >
                        <div className="flex items-center gap-2 text-sm md:text-base font-bold text-amber-700 mb-1">
                          <ChevronRight size={16} />
                          +{t.scoreDelta} {t.name}
                        </div>
                        <p className="text-sm md:text-base text-slate-600 leading-6">
                          {t.explanation}
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-slate-500">
                      Không có dữ liệu suy luận AI.
                    </div>
                  )}
                </div>
              </section>
            </div>

            {/* TOP RECOMMENDATION */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-7">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-11 h-11 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center">
                  <CheckCircle size={20} />
                </div>
                <div>
                  <h3 className="text-xl md:text-2xl font-bold text-slate-900">Top Recommendation</h3>
                  <p className="text-sm md:text-base text-slate-500">Danh sách laptop phù hợp nhất</p>
                </div>
              </div>

              {!data.results || data.results.length === 0 ? (
                <div className="rounded-3xl border border-rose-200 bg-rose-50 p-8 md:p-10 text-center">
                  <Zap size={46} className="mx-auto text-rose-500 mb-4" />
                  <h4 className="text-2xl font-bold text-slate-900 mb-2">Không tìm thấy máy phù hợp</h4>
                  <p className="text-base text-slate-600 mb-6 max-w-2xl mx-auto leading-7">
                    Bộ lọc hiện tại đang khá chặt. Không có laptop nào đáp ứng đầy đủ các tiêu chí về ngân sách và cấu hình bạn vừa chọn.
                  </p>
                  <button
                    onClick={() => navigate('/')}
                    className="px-6 py-3 rounded-2xl bg-sky-600 hover:bg-sky-700 text-white font-semibold text-base transition"
                  >
                    Quay lại bộ lọc
                  </button>
                </div>
              ) : (
                <div className="space-y-5">
                  {data.results.map((item) => (
                    <div
                      key={item.laptopId}
                      onClick={() => setSelectedLaptop(item)}
                      className="group rounded-3xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-sky-300 p-5 md:p-6 transition cursor-pointer"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-[180px_1fr] gap-5 md:gap-6 items-center">
                        <div className="h-40 rounded-2xl bg-white border border-slate-200 flex items-center justify-center p-4">
                          {item.imageUrl && (
                            <img
                              src={item.imageUrl}
                              alt={item.laptopName}
                              className="max-w-full max-h-full object-contain transition-transform duration-300 group-hover:scale-105"
                            />
                          )}
                        </div>

                        <div className="space-y-4">
                          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                            <div>
                              <h4 className="text-xl md:text-2xl font-bold text-slate-900 leading-snug">
                                {item.laptopName}
                              </h4>
                              <div className="mt-2 flex flex-wrap items-center gap-3">
                                <span className="px-3 py-1 rounded-full bg-sky-100 text-sky-700 text-sm font-semibold">
                                  {item.brand}
                                </span>
                                <span className="text-base md:text-lg font-semibold text-slate-700">
                                  {item.price?.toLocaleString() || "Đang cập nhật"} VND
                                </span>
                              </div>
                            </div>

                            <div className="shrink-0 text-left lg:text-right">
                              <p className="text-sm text-slate-500 font-medium mb-1">Độ phù hợp</p>
                              <p className="text-3xl md:text-4xl font-extrabold text-rose-600">
                                {item.matchPercent ?? 0}%
                              </p>
                            </div>
                          </div>

                          <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-rose-500 to-orange-400 rounded-full"
                              style={{ width: `${item.matchPercent ?? 0}%` }}
                            />
                          </div>

                          <div className="flex flex-wrap gap-2">
                            {item.reasons?.map((r, idx) => (
                              <span
                                key={idx}
                                className="px-3 py-1 rounded-full bg-rose-100 text-rose-700 text-sm font-medium"
                              >
                                {r.badgeLabel || r}
                              </span>
                            ))}
                          </div>

                          <div className="text-sm font-medium text-sky-700 flex items-center gap-1">
                            Xem chi tiết <ChevronRight size={16} />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* RIGHT */}
          <div className="xl:col-span-4">
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-7 xl:sticky xl:top-6 space-y-8">
              {/* AHP WEIGHTS */}
              <div>
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-11 h-11 rounded-2xl bg-indigo-100 text-indigo-600 flex items-center justify-center">
                    <Cpu size={20} />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-slate-900">Kết quả trọng số AHP</h3>
                    <p className="text-sm text-slate-500">Mức độ ưu tiên của từng tiêu chí</p>
                  </div>
                </div>

                <div className="space-y-5">
                  {data.ahp?.weights?.map(w => (
                    <div key={w.criterion} className="group relative">
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <div className="flex items-center gap-1.5 text-sm md:text-base font-semibold text-slate-700">
                          {w.name}
                          <Info size={14} className="text-slate-400 group-hover:text-sky-600 transition-colors" />
                        </div>
                        <div className="text-sm md:text-base font-bold text-sky-700">
                          {((w.weight || 0) * 100).toFixed(1)}%
                        </div>
                      </div>

                      <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-sky-500 rounded-full"
                          style={{ width: `${(w.weight || 0) * 100}%` }}
                        />
                      </div>

                      {w.explanation && (
                        <div className="absolute left-0 bottom-full mb-2 w-full rounded-2xl bg-slate-900 text-white text-sm p-3 shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition z-20">
                          {w.explanation}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* CONSISTENCY */}
              <div className="border-t border-slate-200 pt-6">
                <h4 className="text-base font-bold text-slate-900 mb-4">Chỉ số nhất quán</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4 text-center">
                    <p className="text-sm text-slate-500 mb-1">CI</p>
                    <p className="text-xl font-bold text-slate-900">
                      {data.ahp?.consistency?.ci?.toFixed(3) ?? "-"}
                    </p>
                  </div>

                  <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4 text-center">
                    <p className="text-sm text-slate-500 mb-1">CR</p>
                    <p className={`text-xl font-bold ${(data.ahp?.consistency?.cr ?? 1) < 0.1 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {data.ahp?.consistency?.cr?.toFixed(3) ?? "-"}
                    </p>
                  </div>
                </div>
              </div>

              {/* PAIRWISE MATRIX */}
              {criteriaMatrix.length > 0 && matrixLabels.length > 0 && (
                <div className="border-t border-slate-200 pt-6">
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <h4 className="text-base font-bold text-slate-900">Ma trận so sánh cặp</h4>
                    <button
                      onClick={() => setShowMatrixModal(true)}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-sky-50 hover:bg-sky-100 text-sky-700 text-sm font-semibold transition"
                    >
                      <Maximize2 size={16} />
                      Mở rộng
                    </button>
                  </div>

                  <div className="overflow-x-auto rounded-2xl border border-slate-200">
                    <table className="w-full text-sm text-center bg-white">
                      <thead>
                        <tr className="bg-slate-50">
                          <th className="p-3 border-b border-r border-slate-200 text-slate-600 font-bold">Tiêu chí</th>
                          {matrixLabels.map(l => (
                            <th key={l} className="p-3 border-b border-slate-200 text-slate-600 font-bold whitespace-nowrap">
                              {l}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {criteriaMatrix.map((row, i) => (
                          <tr key={i} className="hover:bg-slate-50">
                            <td className="p-3 border-b border-r border-slate-200 text-left font-semibold text-slate-700 whitespace-nowrap">
                              {matrixLabels[i]}
                            </td>
                            {row.map((val, j) => (
                              <td key={j} className="p-3 border-b border-slate-200 text-sky-700 font-medium">
                                {Number.isInteger(val) ? val : val?.toFixed(2)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* NORMALIZED MATRIX */}
              {normalizedMatrix.length > 0 && matrixLabels.length > 0 && (
                <div className="border-t border-slate-200 pt-6">
                  <h4 className="text-base font-bold text-slate-900 mb-4">Ma trận chuẩn hóa</h4>

                  <div className="overflow-x-auto rounded-2xl border border-slate-200">
                    <table className="w-full text-sm text-center bg-white">
                      <thead>
                        <tr className="bg-slate-50">
                          <th className="p-3 border-b border-r border-slate-200 text-slate-600 font-bold">Tiêu chí</th>
                          {matrixLabels.map(l => (
                            <th key={l} className="p-3 border-b border-slate-200 text-slate-600 font-bold whitespace-nowrap">
                              {l}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {normalizedMatrix.map((row, i) => (
                          <tr key={i} className="hover:bg-slate-50">
                            <td className="p-3 border-b border-r border-slate-200 text-left font-semibold text-slate-700 whitespace-nowrap">
                              {matrixLabels[i]}
                            </td>
                            {row.map((val, j) => (
                              <td key={j} className="p-3 border-b border-slate-200 text-emerald-600 font-medium">
                                {Number.isInteger(val) ? val : val?.toFixed(3)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          </div>
        </div>
      </div>

      {/* MODAL CHI TIẾT LAPTOP */}
      {selectedLaptop && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6">
          <div
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
            onClick={() => setSelectedLaptop(null)}
          ></div>

          <div className="relative w-full max-w-6xl max-h-[92vh] overflow-hidden rounded-3xl bg-white border border-slate-200 shadow-2xl flex flex-col">
            <button
              onClick={() => setSelectedLaptop(null)}
              className="absolute top-4 right-4 z-10 w-11 h-11 rounded-full bg-slate-100 hover:bg-rose-100 text-slate-600 hover:text-rose-600 flex items-center justify-center transition"
            >
              <X size={22} />
            </button>

            <div className="p-6 md:p-8 overflow-y-auto custom-scrollbar">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 md:gap-10">
                <div>
                  <div className="h-72 rounded-3xl bg-slate-50 border border-slate-200 flex items-center justify-center p-6 relative mb-6">
                    <div className="absolute top-4 left-4 px-3 py-1 rounded-full bg-sky-100 text-sky-700 text-sm font-semibold">
                      {selectedLaptop.brand}
                    </div>
                    {selectedLaptop.imageUrl && (
                      <img
                        src={selectedLaptop.imageUrl}
                        alt={selectedLaptop.laptopName}
                        className="max-w-full max-h-full object-contain"
                      />
                    )}
                  </div>

                  <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900 leading-snug mb-2">
                    {selectedLaptop.laptopName}
                  </h2>
                  <p className="text-xl md:text-2xl font-bold text-sky-700 mb-6">
                    {selectedLaptop.price?.toLocaleString() || "Đang cập nhật"} VND
                  </p>

                  {selectedLaptop.reasons?.length > 0 && (
                    <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 md:p-6">
                      <h4 className="text-base font-bold text-rose-700 mb-4 flex items-center gap-2">
                        <Bot size={18} />
                        Phân tích lý do
                      </h4>

                      <ul className="space-y-3">
                        {selectedLaptop.reasons.map((reason, idx) => (
                          <li key={idx} className="flex items-start gap-3 text-sm md:text-base text-slate-700">
                            <CheckCircle size={18} className="text-rose-500 shrink-0 mt-0.5" />
                            <span>{reason.badgeLabel || reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="flex flex-col justify-center">
                  <div className="flex items-end justify-between gap-4 border-b border-slate-200 pb-5 mb-6">
                    <div>
                      <h3 className="text-xl font-bold text-slate-900">Performance Telemetry</h3>
                      <p className="text-sm md:text-base text-slate-500 mt-1">
                        Điểm chi tiết theo từng tiêu chí
                      </p>
                    </div>

                    <div className="text-right">
                      <p className="text-sm text-slate-500 mb-1">Total Match</p>
                      <p className="text-4xl md:text-5xl font-extrabold text-rose-600">
                        {selectedLaptop.matchPercent ?? 0}%
                      </p>
                    </div>
                  </div>

                  <div className="space-y-5">
                    {Object.entries(selectedLaptop.criteriaScores || {}).map(([crit, score], idx) => {
                      const colors = [
                        'bg-blue-500',
                        'bg-purple-500',
                        'bg-green-500',
                        'bg-yellow-500',
                        'bg-teal-500',
                        'bg-orange-500',
                        'bg-red-500',
                        'bg-pink-500'
                      ];
                      const color = colors[idx % colors.length];

                      return (
                        <div key={idx}>
                          <div className="flex justify-between items-center gap-3 mb-2">
                            <span className="text-sm md:text-base font-semibold text-slate-700 uppercase">
                              {crit}
                            </span>
                            <span className="text-sm md:text-base font-bold text-slate-900">
                              {score} <span className="text-slate-400">/100</span>
                            </span>
                          </div>
                          <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${color} rounded-full`}
                              style={{ width: `${score}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <button
                    onClick={() =>
                      window.open(`https://www.google.com/search?q=mua+laptop+${selectedLaptop.laptopName}`, '_blank')
                    }
                    className="w-full mt-8 rounded-2xl bg-sky-600 hover:bg-sky-700 text-white font-semibold text-base py-3.5 transition"
                  >
                    Tìm nơi mua sản phẩm này
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL MA TRẬN */}
      {showMatrixModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 md:p-6">
          <div
            className="absolute inset-0 bg-slate-900/70 backdrop-blur-sm"
            onClick={() => setShowMatrixModal(false)}
          ></div>

          <div className="relative w-full max-w-7xl max-h-[94vh] overflow-hidden rounded-3xl bg-white border border-slate-200 shadow-2xl flex flex-col">
            <div className="flex items-center justify-between gap-4 p-6 border-b border-slate-200">
              <div>
                <h2 className="text-2xl md:text-3xl font-bold text-slate-900 flex items-center gap-3">
                  <Cpu size={26} className="text-sky-700" />
                  Chi tiết Ma trận AHP
                </h2>
                <p className="text-sm md:text-base text-slate-500 mt-1">
                  Bảng tính toán trọng số theo phương pháp Saaty
                </p>
              </div>

              <button
                onClick={() => setShowMatrixModal(false)}
                className="w-11 h-11 rounded-full bg-slate-100 hover:bg-rose-100 text-slate-600 hover:text-rose-600 flex items-center justify-center transition"
              >
                <X size={22} />
              </button>
            </div>

            <div className="p-6 overflow-y-auto custom-scrollbar space-y-10">
              <div>
                <h4 className="text-xl font-bold text-sky-700 mb-4">
                  1. Ma trận So sánh cặp (Pairwise Matrix)
                </h4>
                <div className="overflow-x-auto rounded-2xl border border-slate-200">
                  <table className="w-full text-center text-base bg-white">
                    <thead>
                      <tr className="bg-slate-50">
                        <th className="p-4 border-b border-r border-slate-200 text-slate-700 font-bold">Tiêu chí</th>
                        {matrixLabels.map(l => (
                          <th key={l} className="p-4 border-b border-slate-200 text-slate-700 font-bold whitespace-nowrap">
                            {l}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {criteriaMatrix.map((row, i) => (
                        <tr key={i} className="hover:bg-slate-50">
                          <td className="p-4 border-b border-r border-slate-200 text-left text-slate-800 font-semibold whitespace-nowrap">
                            {matrixLabels[i]}
                          </td>
                          {row.map((val, j) => (
                            <td key={j} className="p-4 border-b border-slate-200 text-sky-700 font-medium">
                              {Number.isInteger(val) ? val : val?.toFixed(2)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h4 className="text-xl font-bold text-emerald-600 mb-4">
                  2. Ma trận Chuẩn hóa (Normalized Matrix)
                </h4>
                <div className="overflow-x-auto rounded-2xl border border-slate-200">
                  <table className="w-full text-center text-base bg-white">
                    <thead>
                      <tr className="bg-slate-50">
                        <th className="p-4 border-b border-r border-slate-200 text-slate-700 font-bold">Tiêu chí</th>
                        {matrixLabels.map(l => (
                          <th key={l} className="p-4 border-b border-slate-200 text-slate-700 font-bold whitespace-nowrap">
                            {l}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {normalizedMatrix.map((row, i) => (
                        <tr key={i} className="hover:bg-slate-50">
                          <td className="p-4 border-b border-r border-slate-200 text-left text-slate-800 font-semibold whitespace-nowrap">
                            {matrixLabels[i]}
                          </td>
                          {row.map((val, j) => (
                            <td key={j} className="p-4 border-b border-slate-200 text-emerald-600 font-medium">
                              {Number.isInteger(val) ? val : val?.toFixed(3)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}