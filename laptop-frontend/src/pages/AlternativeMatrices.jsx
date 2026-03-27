import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Activity, ArrowLeft } from 'lucide-react';
import { getAlternativeAHP, getDashboard } from '../services/api';

function formatValue(value, decimals = 3) {
  const num = Number(value ?? 0);
  if (Number.isNaN(num)) return '-';
  if (Number.isInteger(num)) return String(num);
  return num.toFixed(decimals);
}

function buildSquareMatrix(flatRows, keys, rowField = 'row', colField = 'col', valueField = 'value') {
  return keys.map((rowKey) =>
    keys.map((colKey) => {
      const cell = flatRows.find((item) => String(item[rowField]) === String(rowKey) && String(item[colField]) === String(colKey));
      return cell ? cell[valueField] : 0;
    })
  );
}

function MatrixTable({
  title,
  caption,
  headers,
  rowHeaders,
  values,
  cornerLabel = 'Phương án',
  valueClassName = 'text-slate-700',
  decimals = 3,
}) {
  if (!headers?.length || !rowHeaders?.length || !values?.length) {
    return null;
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 md:p-5 shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg md:text-xl font-bold text-slate-900">{title}</h3>
        {caption ? <p className="text-sm text-slate-500 mt-1">{caption}</p> : null}
      </div>

      <div className="overflow-auto rounded-2xl border border-slate-200 max-h-[72vh]">
        <table className="w-full min-w-max text-xs text-center bg-white">
          <thead>
            <tr className="bg-slate-50">
              <th className="p-2.5 border-b border-r border-slate-200 text-slate-600 font-bold">{cornerLabel}</th>
              {headers.map((header) => (
                <th key={header} className="p-2.5 border-b border-slate-200 text-slate-600 font-bold whitespace-nowrap">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {values.map((row, rowIndex) => (
              <tr key={rowHeaders[rowIndex]} className="hover:bg-slate-50">
                <td className="p-2.5 border-b border-r border-slate-200 text-left font-semibold text-slate-700 whitespace-nowrap">
                  {rowHeaders[rowIndex]}
                </td>
                {row.map((cell, cellIndex) => (
                  <td
                    key={`${rowHeaders[rowIndex]}-${headers[cellIndex]}`}
                    className={`p-2.5 border-b border-slate-200 font-medium ${valueClassName}`}
                  >
                    {formatValue(cell, decimals)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const criterionLabelsMap = {
  cpu: 'CPU',
  gpu: 'GPU',
  ram: 'RAM',
  screen: 'Màn hình',
  weight: 'Trọng lượng',
  battery: 'Pin',
  durability: 'Độ bền',
  upgradeability: 'Nâng cấp'
};

export default function AlternativeMatrices() {
  const { sessionKey } = useParams();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [alternativeAHP, setAlternativeAHP] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let isMounted = true;

    Promise.all([
      getDashboard(sessionKey),
      getAlternativeAHP(sessionKey).catch((err) => ({
        data: {
          alternatives: [],
          criterionTables: [],
          message: err?.response?.data?.message || 'Không tải được dữ liệu ma trận phương án.',
        },
      })),
    ])
      .then(([dashboardRes, altRes]) => {
        if (!isMounted) return;
        setDashboard(dashboardRes?.data || null);
        setAlternativeAHP(altRes?.data || null);
        setErrorMessage(altRes?.data?.message || '');
      })
      .catch((err) => console.error('Lỗi khi tải trang ma trận phương án', err));

    return () => {
      isMounted = false;
    };
  }, [sessionKey]);

  const criteriaWeights = dashboard?.ahp?.weights || [];
  const criterionWeightMap = useMemo(
    () => Object.fromEntries(criteriaWeights.map((item) => [item.criterion, Number(item.weight || 0)])),
    [criteriaWeights]
  );

  const alternatives = alternativeAHP?.alternatives || [];
  const alternativeAliasMap = useMemo(
    () => Object.fromEntries(alternatives.map((item, index) => [String(item.laptopId), `PA${index + 1}`])),
    [alternatives]
  );

  const sortedAlternativeTables = useMemo(() => {
    const order = new Map(criteriaWeights.map((item, index) => [item.criterion, index]));
    return [...(alternativeAHP?.criterionTables || [])].sort(
      (a, b) => (order.get(a.criterion) ?? Number.MAX_SAFE_INTEGER) - (order.get(b.criterion) ?? Number.MAX_SAFE_INTEGER)
    );
  }, [alternativeAHP?.criterionTables, criteriaWeights]);

  if (!dashboard) {
    return (
      <div className="w-full min-h-screen bg-slate-100 flex items-center justify-center px-6">
        <div className="text-xl font-bold text-sky-700 animate-pulse">Đang tải ma trận phương án...</div>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen bg-slate-100 text-slate-900">
      <div className="w-full px-4 py-6 md:px-8 md:py-8">
        <div className="w-full space-y-6">
          <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-8">
            <div className="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-6">
              <div className="space-y-4">
                <button
                  onClick={() => navigate(`/dashboard/${sessionKey}`)}
                  className="inline-flex items-center gap-2 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 font-semibold transition"
                >
                  <ArrowLeft size={18} />
                  Quay lại dashboard
                </button>

                <div>
                  <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-slate-900">
                    Ma trận phương án theo từng tiêu chí
                  </h1>
                  <p className="text-sm md:text-base text-slate-500 mt-2 max-w-4xl">
                    Trang này tập trung riêng vào 8 ma trận so sánh cặp phương án sau khi AI shortlist, để bạn dễ kéo và đối chiếu hơn.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 min-w-full xl:min-w-[360px] xl:max-w-[420px]">
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4">
                  <p className="text-xs md:text-sm text-slate-500 font-semibold uppercase tracking-wide mb-2">
                    AI shortlist
                  </p>
                  <p className="text-2xl md:text-3xl font-extrabold text-emerald-600">
                    {dashboard.session?.aiShortlistCount ?? alternatives.length}
                  </p>
                </div>

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4">
                  <p className="text-xs md:text-sm text-slate-500 font-semibold uppercase tracking-wide mb-2">
                    Số ma trận
                  </p>
                  <p className="text-2xl md:text-3xl font-extrabold text-fuchsia-700">
                    {sortedAlternativeTables.length}
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-7">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-2xl bg-fuchsia-100 text-fuchsia-700 flex items-center justify-center">
                <Activity size={20} />
              </div>
              <div>
                <h2 className="text-xl md:text-2xl font-bold text-slate-900">Danh sách phương án đang so sánh</h2>
                <p className="text-sm text-slate-500">Ký hiệu PA1, PA2... được dùng xuyên suốt toàn bộ 8 ma trận bên dưới.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {alternatives.map((item, index) => (
                <div key={item.laptopId} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="inline-flex items-center gap-2 rounded-full bg-slate-900 text-white px-3 py-1 text-xs font-bold uppercase tracking-wide mb-3">
                    PA{index + 1}
                  </div>
                  <h4 className="font-bold text-slate-900 leading-6">{item.laptopName}</h4>
                  <p className="text-sm text-slate-500 mt-2">{item.brand || 'Không rõ thương hiệu'}</p>
                </div>
              ))}
            </div>
          </section>

          {sortedAlternativeTables.length > 0 ? (
            <div className="space-y-6">
              {sortedAlternativeTables.map((table) => {
                const alternativeIds = table.alternativeWeights?.map((item) => item.laptopId) || [];
                const headers = alternativeIds.map((id) => alternativeAliasMap[String(id)] || String(id));
                const rowHeaders = headers;
                const matrixValues = buildSquareMatrix(
                  table.pairwiseMatrix || [],
                  alternativeIds,
                  'rowLaptopId',
                  'colLaptopId',
                  'value'
                );

                return (
                  <section key={table.criterion} className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-7 space-y-6">
                    <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
                      <div>
                        <div className="inline-flex items-center gap-2 rounded-full bg-fuchsia-50 text-fuchsia-700 px-3 py-1 text-xs font-semibold uppercase tracking-wider mb-3">
                          {criterionLabelsMap[table.criterion] || table.name}
                        </div>
                        <h3 className="text-xl md:text-2xl font-bold text-slate-900">{table.name}</h3>
                        <p className="text-sm md:text-base text-slate-500 mt-2 max-w-3xl">
                          Ma trận này so sánh từng cặp laptop theo tiêu chí "{table.name}" để rút ra trọng số phương án.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 min-w-full xl:min-w-[320px] xl:max-w-[420px]">
                        <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4">
                          <p className="text-sm text-slate-500 mb-1">Trọng số tiêu chí</p>
                          <p className="text-2xl font-extrabold text-sky-700">
                            {((criterionWeightMap[table.criterion] || 0) * 100).toFixed(1)}%
                          </p>
                        </div>
                        <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4">
                          <p className="text-sm text-slate-500 mb-1">CR phương án</p>
                          <p className={`text-2xl font-extrabold ${(table.consistency?.cr ?? 1) < 0.1 ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {table.consistency?.cr != null ? formatValue(table.consistency?.cr, 3) : '-'}
                          </p>
                        </div>
                      </div>
                    </div>

                    <MatrixTable
                      title={`Ma trận so sánh cặp phương án - ${table.name}`}
                      caption="Mỗi ô là tỷ lệ ưu tiên tương đối giữa 2 phương án theo tiêu chí đang xét."
                      headers={headers}
                      rowHeaders={rowHeaders}
                      values={matrixValues}
                      cornerLabel="Phương án"
                      valueClassName="text-fuchsia-700"
                      decimals={2}
                    />

                    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5 md:p-6">
                      <h4 className="text-lg font-bold text-slate-900 mb-4">Trọng số phương án theo tiêu chí</h4>
                      <div className="overflow-auto rounded-2xl border border-slate-200 bg-white max-h-[50vh]">
                        <table className="w-full min-w-max text-sm">
                          <thead>
                            <tr className="bg-slate-50 text-slate-600">
                              <th className="p-3 border-b border-slate-200 text-left font-bold">PA</th>
                              <th className="p-3 border-b border-slate-200 text-left font-bold">Laptop</th>
                              <th className="p-3 border-b border-slate-200 text-right font-bold">Điểm tiêu chí</th>
                              <th className="p-3 border-b border-slate-200 text-right font-bold">Trọng số PA</th>
                            </tr>
                          </thead>
                          <tbody>
                            {table.alternativeWeights?.map((item) => (
                              <tr key={`${table.criterion}-${item.laptopId}`} className="hover:bg-slate-50">
                                <td className="p-3 border-b border-slate-200 font-semibold text-slate-700 whitespace-nowrap">
                                  {alternativeAliasMap[String(item.laptopId)] || item.laptopId}
                                </td>
                                <td className="p-3 border-b border-slate-200 text-slate-700">
                                  <div className="font-semibold">{item.laptopName}</div>
                                  <div className="text-xs text-slate-500 mt-1">{item.brand || 'Không rõ thương hiệu'}</div>
                                </td>
                                <td className="p-3 border-b border-slate-200 text-right text-slate-700 font-medium">
                                  {formatValue(item.criterionUtility, 2)}
                                </td>
                                <td className="p-3 border-b border-slate-200 text-right font-bold text-fuchsia-700">
                                  {formatValue(item.alternativePriority, 4)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </section>
                );
              })}
            </div>
          ) : (
            <div className="rounded-3xl border border-amber-200 bg-amber-50 p-6 text-amber-800">
              <p className="font-semibold mb-2">Chưa có dữ liệu ma trận phương án.</p>
              <p className="leading-7">{errorMessage || 'Hãy chạy lại session mới sau khi backend đã restart.'}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
