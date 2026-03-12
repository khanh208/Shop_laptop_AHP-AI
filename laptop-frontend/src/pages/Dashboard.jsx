import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getDashboard, getInferenceTrace, getCandidates } from '../services/api';
import { Activity, Filter, Cpu, CheckCircle, X, ChevronRight, Zap, Bot, Info } from 'lucide-react';

export default function Dashboard() {
  const { sessionKey } = useParams();
  const [data, setData] = useState(null);
  const [trace, setTrace] = useState([]);
  const [candidates, setCandidates] = useState(null);
  const [selectedLaptop, setSelectedLaptop] = useState(null);

  useEffect(() => {
    Promise.all([
      getDashboard(sessionKey),
      getInferenceTrace(sessionKey),
      getCandidates(sessionKey)
    ]).then(([dashRes, traceRes, candRes]) => {
      setData(dashRes.data);
      setTrace(traceRes.data.trace);
      setCandidates(candRes.data);
    }).catch(err => console.error("Lỗi khi tải dữ liệu Dashboard", err));
  }, [sessionKey]);

  if (!data) return (
    <div className="bg-[#06080a] min-h-screen text-white flex items-center justify-center font-mono italic text-2xl animate-pulse text-formula-red">
      <Zap className="mr-3 animate-bounce" /> LOADING REAL TELEMETRY DATA...
    </div>
  );

  // Chỉ lấy đúng dữ liệu từ backend, nếu không có thì để mảng rỗng để không bị crash
  // 1. Lấy danh sách tên Tiêu chí và Mã tiêu chí (để làm cột và hàng)
  const matrixLabels = data.ahp?.weights?.map(w => w.name) || [];
  const criteriaCodes = data.ahp?.weights?.map(w => w.criterion) || [];

  // 2. Chuyển đổi pairwiseMatrix từ Backend (Mảng 1 chiều) thành criteriaMatrix (Mảng 2 chiều)
  const flatMatrix = data.ahp?.pairwiseMatrix || [];
  const criteriaMatrix = [];

  if (flatMatrix.length > 0 && criteriaCodes.length > 0) {
    // Vòng lặp tạo 8 hàng
    for (let i = 0; i < criteriaCodes.length; i++) {
      const rowArray = [];
      // Vòng lặp tạo 8 cột trong mỗi hàng
      for (let j = 0; j < criteriaCodes.length; j++) {
        // Tìm giá trị giao nhau giữa Hàng i và Cột j
        const cell = flatMatrix.find(
          c => c.row === criteriaCodes[i] && c.col === criteriaCodes[j]
        );
        rowArray.push(cell ? cell.value : 0);
      }
      criteriaMatrix.push(rowArray);
    }
  }

  return (
    <div className="min-h-screen bg-[#06080a] text-white p-6 md:p-10 font-sans relative">
      <div className="border-b border-gray-800 pb-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h2 className="text-formula-red font-bold uppercase tracking-[0.3em] text-[10px] mb-2 flex items-center gap-2">
            <Activity size={14} className="animate-pulse" /> Session ID: {sessionKey.slice(0,8)}
          </h2>
          <h1 className="text-4xl md:text-5xl font-black italic tracking-tighter uppercase bg-gradient-to-r from-white to-gray-500 bg-clip-text text-transparent">
            Analysis Dashboard
          </h1>
        </div>
        <div className="text-right bg-formula-darker p-3 rounded-lg border border-gray-800">
          <p className="text-gray-500 text-[10px] uppercase font-bold tracking-widest mb-1">Total Analyzed</p>
          <p className="text-3xl font-mono text-formula-blue leading-none">{data.session?.hardFilterTotalCount ?? 0}</p>
        </div>
      </div>

      {/* KHỐI GỢI Ý AI TỔNG QUAN */}
      {data.aiSuggestion && (
        <div className="bg-gradient-to-r from-[#0d1117] to-black border border-gray-800/60 p-5 md:p-6 rounded-2xl shadow-xl relative overflow-hidden mb-8">
          <div className="absolute top-0 left-0 w-1 h-full bg-formula-red"></div>
          <h2 className="text-formula-red font-black italic uppercase flex items-center gap-3 mb-2 text-sm md:text-base">
            <Bot size={20} /> Tổng quan chiến lược từ AI
          </h2>
          <p className="text-gray-300 text-xs md:text-sm leading-relaxed max-w-5xl">
            {data.aiSuggestion}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        
        {/* CỘT TRÁI */}
        <div className="xl:col-span-1 space-y-6">
          <section className="bg-[#0d1117] p-6 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-formula-blue"></div>
            <div className="flex items-center gap-2 mb-6 text-formula-blue uppercase font-black text-xs tracking-widest">
              <Filter size={16} /> Vòng loại (Khối A)
            </div>
            <div className="flex items-end gap-2">
              <span className="text-5xl font-black">{data.session?.hardFilterPassCount ?? 0}</span>
              <span className="text-gray-500 font-mono mb-1">/ {data.session?.hardFilterTotalCount ?? 0}</span>
            </div>
            <p className="text-[10px] text-gray-400 uppercase tracking-widest mt-2">Máy đạt chuẩn phần cứng</p>
          </section>

          <section className="bg-[#0d1117] p-6 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-yellow-500"></div>
            <div className="flex items-center gap-2 mb-4 text-yellow-500 uppercase font-black text-xs tracking-widest">
              <Activity size={16} /> Suy luận AI (Khối B)
            </div>
            <div className="space-y-3 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
              {trace?.filter(t => t.sourceType === 'filter').map((t, i) => (
                <div key={i} className="text-[10px] leading-relaxed bg-black/40 p-3 rounded-lg border border-gray-800/50">
                  <span className="text-yellow-500 font-black block mb-1 flex items-center gap-1">
                    <ChevronRight size={12}/> +{t.scoreDelta} {t.name}
                  </span>
                  <span className="text-gray-400">{t.explanation}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* CỘT GIỮA */}
        <div className="xl:col-span-2 space-y-6">
          <div className="flex items-center gap-3 mb-4 text-formula-red uppercase font-black text-sm italic tracking-widest border-b border-gray-800 pb-2">
            <CheckCircle size={18} /> Top Recommendation (Khối E)
          </div>
          
          <div className="space-y-5">
            {data.results?.map((item) => (
              <div 
                key={item.laptopId} 
                onClick={() => setSelectedLaptop(item)}
                className="group relative bg-[#0d1117] border border-gray-800 hover:border-formula-red transition-all duration-300 p-5 rounded-2xl cursor-pointer shadow-lg hover:shadow-[0_0_20px_rgba(225,6,0,0.2)] hover:-translate-y-1 overflow-hidden flex flex-col md:flex-row gap-6"
              >
                <div className="absolute top-0 left-0 w-1.5 h-full bg-formula-red shadow-[0_0_15px_rgba(225,6,0,0.5)]"></div>
                
                <div className="w-full md:w-48 h-32 bg-black/50 rounded-xl flex items-center justify-center p-4 border border-gray-800/50 group-hover:border-formula-red/30 transition-colors">
                  {item.imageUrl && <img src={item.imageUrl} className="max-w-full max-h-full object-contain drop-shadow-2xl transition-transform duration-500 group-hover:scale-110" alt={item.laptopName} />}
                </div>
                
                <div className="flex-1 flex flex-col justify-center">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-xl font-black uppercase tracking-tighter text-gray-200 group-hover:text-white transition-colors">{item.laptopName}</h3>
                    <div className="text-3xl font-black text-formula-red italic drop-shadow-[0_0_10px_rgba(225,6,0,0.3)]">{item.matchPercent ?? 0}%</div>
                  </div>
                  
                  <div className="flex items-center gap-3 mb-4">
                    <span className="bg-gradient-to-r from-formula-blue to-blue-700 text-white text-[10px] font-black px-3 py-1 rounded-md uppercase tracking-wider shadow-lg">
                      {item.brand}
                    </span>
                    <span className="text-formula-blue font-mono text-sm">{item.price?.toLocaleString() || "Đang cập nhật"} VND</span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {item.reasons?.map((r, idx) => (
                      <span key={idx} className="bg-formula-red/10 text-formula-red text-[9px] font-bold px-2.5 py-1 rounded-md uppercase border border-formula-red/20">{r}</span>
                    ))}
                  </div>
                </div>
                
                <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <span className="text-[9px] text-gray-400 uppercase font-bold flex items-center gap-1 bg-black/50 px-2 py-1 rounded-full backdrop-blur-sm">
                    Click xem chi tiết <ChevronRight size={10} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CỘT PHẢI */}
        <div className="xl:col-span-1 space-y-6">
          <section className="bg-[#0d1117] p-6 rounded-2xl border border-gray-800 shadow-xl sticky top-8">
            <div className="flex items-center gap-2 mb-8 text-formula-blue uppercase font-black text-xs tracking-widest">
              <Cpu size={16} /> Phân tích AHP (Khối C)
            </div>
            
            <div className="space-y-6">
              {data.ahp?.weights?.map(w => (
                <div key={w.criterion} className="relative group">
                  <div className="flex justify-between text-[10px] mb-2 uppercase font-bold tracking-wider">
                    <span className="text-gray-400 flex items-center gap-1 cursor-help">
                      {w.name} <Info size={10} className="text-gray-600 group-hover:text-formula-blue transition-colors"/>
                    </span>
                    <span className="text-formula-blue">{((w.weight || 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-800 w-full rounded-full overflow-hidden shadow-inner">
                    <div className="h-full bg-gradient-to-r from-formula-blue to-blue-400 relative" style={{ width: `${(w.weight || 0) * 100}%` }}>
                       <div className="absolute top-0 right-0 w-2 h-full bg-white/50 blur-[1px]"></div>
                    </div>
                  </div>
                  
                  {w.description && (
                    <div className="absolute left-0 bottom-full mb-2 w-full bg-black/90 backdrop-blur-sm border border-gray-700 text-gray-300 text-[10px] p-2.5 rounded shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 z-20">
                      {w.description}
                      <div className="absolute left-4 -bottom-1 border-t-4 border-t-gray-700 border-l-4 border-l-transparent border-r-4 border-r-transparent"></div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-8 pt-6 border-t border-gray-800/50">
               <h4 className="text-[10px] text-gray-500 uppercase font-black mb-3 tracking-widest">Chỉ số nhất quán (Khối D)</h4>
               <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                  <div className="bg-black/40 p-3 rounded-xl border border-gray-800 text-center text-gray-400">CI: <span className="text-white">{data.ahp?.consistency?.ci?.toFixed(3) ?? "-"}</span></div>
                  <div className={`bg-black/40 p-3 rounded-xl border border-gray-800 text-center ${(data.ahp?.consistency?.cr ?? 1) < 0.1 ? 'text-green-500' : 'text-red-500'}`}>
                    CR: <span className="font-bold">{data.ahp?.consistency?.cr?.toFixed(3) ?? "-"}</span>
                  </div>
               </div>
            </div>

            {/* Render Ma trận chỉ khi backend thực sự gửi về */}
            {criteriaMatrix.length > 0 && matrixLabels.length > 0 && (
              <div className="mt-6 pt-6 border-t border-gray-800/50">
                 <h4 className="text-[10px] text-gray-500 uppercase font-black mb-3 tracking-widest">Ma trận so sánh cặp</h4>
                 <div className="overflow-x-auto rounded-lg border border-gray-800">
                   <table className="w-full text-center text-[10px] font-mono bg-black/30">
                     <thead>
                       <tr className="bg-gray-900">
                         <th className="p-2 border-b border-r border-gray-800 text-gray-500">Tiêu chí</th>
                         {matrixLabels.map(l => <th key={l} className="p-2 border-b border-gray-800 text-gray-400 truncate max-w-[50px]">{l}</th>)}
                       </tr>
                     </thead>
                     <tbody>
                       {criteriaMatrix.map((row, i) => (
                         <tr key={i} className="hover:bg-white/5 transition-colors">
                           <td className="p-2 border-b border-r border-gray-800/50 text-gray-400 text-left font-sans font-bold">{matrixLabels[i]}</td>
                           {row.map((val, j) => (
                             <td key={j} className="p-2 border-b border-gray-800/50 text-formula-blue">
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
          </section>
        </div>
      </div>

      {/* MODAL CHI TIẾT */}
      {selectedLaptop && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
          <div 
            className="absolute inset-0 bg-black/80 backdrop-blur-sm transition-opacity" 
            onClick={() => setSelectedLaptop(null)}
          ></div>

          <div className="relative bg-[#0d1117] border border-gray-700 w-full max-w-5xl rounded-3xl shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200">
            <div className="h-1.5 w-full bg-gradient-to-r from-formula-red via-formula-blue to-transparent"></div>
            <button 
              onClick={() => setSelectedLaptop(null)}
              className="absolute top-4 right-4 p-2 bg-black/50 text-gray-400 hover:text-white rounded-full transition-colors z-10 hover:bg-formula-red"
            >
              <X size={20} />
            </button>

            <div className="p-8 overflow-y-auto custom-scrollbar">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                
                <div>
                  <div className="bg-black/40 border border-gray-800 rounded-2xl p-8 mb-6 flex justify-center items-center h-64 relative">
                    <div className="absolute top-4 left-4 bg-formula-blue text-black text-[10px] font-black px-3 py-1 rounded-md uppercase tracking-wider">
                      {selectedLaptop.brand}
                    </div>
                    {selectedLaptop.imageUrl && <img src={selectedLaptop.imageUrl} alt={selectedLaptop.laptopName} className="max-w-full max-h-full object-contain drop-shadow-2xl" />}
                  </div>
                  
                  <h2 className="text-3xl font-black uppercase italic tracking-tighter mb-2">{selectedLaptop.laptopName}</h2>
                  <p className="text-2xl font-mono text-formula-blue mb-6">{selectedLaptop.price?.toLocaleString() || "Đang cập nhật"} VND</p>
                  
                  {selectedLaptop.reasons?.length > 0 && (
                    <div className="bg-formula-red/10 border border-formula-red/30 rounded-xl p-5 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-16 h-full bg-formula-red/20 skew-x-12 translate-x-4"></div>
                      <h4 className="text-[10px] text-formula-red uppercase font-black tracking-widest mb-3 flex items-center gap-2">
                        <Bot size={14}/> Phân tích lý do (AI Inference)
                      </h4>
                      <ul className="space-y-2">
                        {selectedLaptop.reasons.map((reason, idx) => (
                          <li key={idx} className="text-xs text-gray-300 flex items-start gap-2">
                            <CheckCircle size={14} className="text-formula-red shrink-0 mt-0.5" />
                            <span>{reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="flex flex-col justify-center">
                  <div className="flex justify-between items-end mb-8 border-b border-gray-800 pb-4">
                     <div>
                        <h3 className="text-formula-blue font-black uppercase tracking-widest text-sm mb-1">Performance Telemetry</h3>
                        <p className="text-[10px] text-gray-500 uppercase">Phân tích điểm số cấu hình (Max 100)</p>
                     </div>
                     <div className="text-right">
                        <p className="text-[10px] text-gray-500 uppercase font-bold mb-1">Total Match</p>
                        <p className="text-5xl font-black text-formula-red italic leading-none">{selectedLaptop.matchPercent ?? 0}%</p>
                     </div>
                  </div>

                  <div className="space-y-6">
                    {[
                      { label: 'Sức mạnh CPU', val: selectedLaptop.scores?.cpu ?? 0, color: 'bg-blue-500' },
                      { label: 'Sức mạnh GPU', val: selectedLaptop.scores?.gpu ?? 0, color: 'bg-purple-500' },
                      { label: 'Tốc độ RAM & SSD', val: selectedLaptop.scores?.ram ?? 0, color: 'bg-green-500' },
                      { label: 'Chất lượng Màn hình', val: selectedLaptop.scores?.screen ?? 0, color: 'bg-yellow-500' },
                      { label: 'Tính di động', val: selectedLaptop.scores?.weight ?? 0, color: 'bg-teal-500' },
                      { label: 'Thời lượng Pin', val: selectedLaptop.scores?.battery ?? 0, color: 'bg-orange-500' }
                    ].map((score, idx) => (
                      <div key={idx}>
                        <div className="flex justify-between items-end mb-2">
                           <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">{score.label}</span>
                           <span className="text-sm font-mono font-bold text-white">{score.val} <span className="text-[10px] text-gray-600">/100</span></span>
                        </div>
                        <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden shadow-inner">
                           <div className={`h-full ${score.color} relative transition-all duration-1000 ease-out`} style={{ width: `${score.val}%` }}>
                              <div className="absolute top-0 right-0 w-4 h-full bg-white/30 skew-x-12"></div>
                           </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <button 
                    onClick={() => window.open(`https://www.google.com/search?q=mua+laptop+${selectedLaptop.laptopName}`, '_blank')}
                    className="w-full mt-10 bg-formula-blue hover:bg-blue-600 text-black font-black py-4 rounded-xl uppercase tracking-widest transition-all hover:shadow-[0_0_20px_rgba(0,210,255,0.4)]"
                  >
                    Tìm nơi mua sản phẩm này
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}