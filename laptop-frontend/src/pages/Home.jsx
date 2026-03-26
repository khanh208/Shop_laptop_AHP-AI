import { useEffect, useState } from 'react';
import { getFormOptions, runRecommendation } from '../services/api';
import { useNavigate } from 'react-router-dom';
import {
  Monitor,
  Zap,
  HardDrive,
  Filter,
  LayoutGrid,
  MemoryStick,
  Wallet,
  BatteryCharging,
  Scale,
  ChevronRight,
  BookOpen,
  Briefcase,
  Gamepad2,
  Trophy
} from 'lucide-react';

export default function Home() {
  const [options, setOptions] = useState({
    usageProfiles: [],
    brands: []
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [form, setForm] = useState({
    mode: 'advanced',
    usageProfile: 'student_it',
    budget: { min: 0, max: 200000000 },
    filters: {
      brandCode: null,
      carryOften: false,
      playHeavyGames: false,
      minRamGb: 0,
      minSsdGb: 0,
      screenSizeMin: 0,
      screenSizeMax: 99,
      maxWeightKg: 10,
      minBatteryHours: 0
    }
  });

  useEffect(() => {
    let isMounted = true;
    getFormOptions()
      .then((res) => {
        if (!isMounted) return;
        const payload = res?.data || {};
        setOptions({ 
          usageProfiles: payload.usageProfiles || [], 
          brands: payload.brands || [] 
        });
      })
      .catch((err) => console.error('Lỗi kết nối Backend!', err));
    return () => { isMounted = false; };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await runRecommendation(form);
      const sessionKey = res?.data?.session?.sessionKey;
      if (!sessionKey) throw new Error('Không nhận được sessionKey');
      navigate(`/dashboard/${sessionKey}`);
    } catch (err) {
      console.error(err);
      alert('Lỗi kết nối Backend! Hãy kiểm tra server.');
    } finally {
      setLoading(false);
    }
  };

  // Lọc chỉ lấy các ngành sinh viên để hiện trong Quiz
  const studentProfiles = options.usageProfiles.filter(p => p.code.startsWith('student_'));

  return (
    <div className="w-full min-h-screen bg-slate-100 text-slate-900">
      <div className="w-full px-4 py-6 md:px-8 md:py-8 max-w-5xl mx-auto">
        <div className="w-full space-y-6">
          <section className="relative w-full overflow-hidden rounded-3xl bg-gradient-to-r from-sky-600 via-cyan-500 to-blue-500 text-white shadow-sm p-6 md:p-10">
            <div className="absolute -top-12 -right-10 w-48 h-48 bg-white/10 rounded-full blur-3xl"></div>
            <div className="absolute -bottom-10 left-1/3 w-56 h-56 bg-white/10 rounded-full blur-3xl"></div>

            <div className="relative z-10 grid grid-cols-1 xl:grid-cols-2 gap-8 items-center">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs md:text-sm font-semibold uppercase tracking-wider mb-4">
                  <Zap size={16} />
                  Dành riêng cho sinh viên
                </div>

                <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight leading-tight">
                  Tư Vấn Laptop
                </h1>

                <p className="mt-4 text-sm md:text-base text-white/90 leading-7 max-w-2xl">
                  Hãy trả lời 4 câu hỏi cực nhanh dưới đây, AI sẽ giúp bạn tìm ra chiếc laptop "chân ái" phù hợp nhất với ngành học và túi tiền!
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="rounded-2xl bg-white/15 backdrop-blur-sm border border-white/20 p-4">
                  <BookOpen size={24} className="mb-2 text-sky-200" />
                  <p className="text-sm font-semibold text-white/80">Cá nhân hoá</p>
                  <p className="text-lg font-bold">Theo đúng ngành học</p>
                </div>
                <div className="rounded-2xl bg-white/15 backdrop-blur-sm border border-white/20 p-4">
                  <Trophy size={24} className="mb-2 text-amber-200" />
                  <p className="text-sm font-semibold text-white/80">Chấm điểm thông minh</p>
                  <p className="text-lg font-bold">Bằng AI & Thuật toán</p>
                </div>
              </div>
            </div>
          </section>

          <form onSubmit={handleSubmit} className="space-y-6">
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-8">
              <h2 className="text-xl md:text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-sky-100 text-sky-700 text-sm">1</span>
                Bạn đang học nhóm ngành nào?
              </h2>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {studentProfiles.map((p) => (
                  <button
                    key={p.code}
                    type="button"
                    onClick={() => setForm({ ...form, usageProfile: p.code })}
                    className={`p-5 rounded-2xl border-2 text-left transition-all ${
                      form.usageProfile === p.code 
                      ? 'border-sky-500 bg-sky-50 shadow-md' 
                      : 'border-slate-200 hover:border-sky-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className={`w-12 h-12 rounded-full mb-4 flex items-center justify-center ${
                      form.usageProfile === p.code ? 'bg-sky-500 text-white' : 'bg-slate-100 text-slate-500'
                    }`}>
                      {p.code.includes('it') ? <Monitor size={20} /> : 
                       p.code.includes('design') ? <LayoutGrid size={20} /> :
                       p.code.includes('engineering') ? <Briefcase size={20} /> :
                       <Scale size={20} />}
                    </div>
                    <h3 className="font-bold text-slate-900 mb-2">{p.name}</h3>
                    <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">{p.description}</p>
                  </button>
                ))}
              </div>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-8">
                <h2 className="text-xl md:text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 text-sm">2</span>
                  Di chuyển & Mang vác
                </h2>
                <p className="text-sm text-slate-600 mb-5">
                  Bạn có thường xuyên xách máy lên trường, thư viện hoặc ra quán cafe học bài không?
                </p>
                <div className="flex bg-slate-100 p-1.5 rounded-2xl">
                  <button
                    type="button"
                    onClick={() => setForm({...form, filters: {...form.filters, carryOften: false}})}
                    className={`flex-1 py-3 px-4 rounded-xl text-sm font-semibold transition ${
                      !form.filters.carryOften ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    Không thường xuyên
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({...form, filters: {...form.filters, carryOften: true}})}
                    className={`flex-1 py-3 px-4 rounded-xl text-sm font-semibold transition ${
                      form.filters.carryOften ? 'bg-emerald-500 shadow text-white' : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    Có, rất thường xuyên
                  </button>
                </div>
                {form.filters.carryOften && (
                  <p className="text-xs text-emerald-600 mt-3 font-medium flex items-center gap-1.5">
                    <Zap size={14} /> Hệ thống sẽ ưu tiên tính di động (Nhẹ & Pin trâu)!
                  </p>
                )}
              </section>

              <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-8">
                <h2 className="text-xl md:text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-rose-100 text-rose-700 text-sm">3</span>
                  Giải trí & Chơi Game
                </h2>
                <p className="text-sm text-slate-600 mb-5">
                  Ngoài việc học, bạn có hay chơi các tựa game nặng (như AAA, Valorant, PUBG...) không?
                </p>
                <div className="flex bg-slate-100 p-1.5 rounded-2xl">
                  <button
                    type="button"
                    onClick={() => setForm({...form, filters: {...form.filters, playHeavyGames: false}})}
                    className={`flex-1 py-3 px-4 rounded-xl text-sm font-semibold transition ${
                      !form.filters.playHeavyGames ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    Không, chỉ chơi game nhẹ / Không chơi
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({...form, filters: {...form.filters, playHeavyGames: true}})}
                    className={`flex-1 py-3 px-4 rounded-xl text-sm font-semibold transition ${
                      form.filters.playHeavyGames ? 'bg-rose-500 shadow text-white' : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    Có, hay chơi game nặng
                  </button>
                </div>
                {form.filters.playHeavyGames && (
                  <p className="text-xs text-rose-600 mt-3 font-medium flex items-center gap-1.5">
                    <Gamepad2 size={14} /> Sẽ tăng cường ưu tiên Card đồ hoạ (GPU) mạnh!
                  </p>
                )}
              </section>
            </div>

            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-8">
              <h2 className="text-xl md:text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-100 text-amber-700 text-sm">4</span>
                Ngân sách & Thương hiệu
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <label className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700 mb-3">
                    <Wallet size={18} className="text-amber-600" />
                    Ngân sách tối đa của bạn (hoặc được bố mẹ cho) là bao nhiêu?
                  </label>
                  <select
                    value={form.budget.max}
                    onChange={(e) => setForm({...form, budget: {...form.budget, max: parseInt(e.target.value, 10)}})}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-4 text-base text-slate-900 outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100 transition font-medium"
                  >
                    <option value="15000000">Dưới 15 Triệu (Sinh viên tiết kiệm)</option>
                    <option value="20000000">Dưới 20 Triệu (Phổ thông)</option>
                    <option value="25000000">Dưới 25 Triệu (Khá giả)</option>
                    <option value="35000000">Dưới 35 Triệu (Dư dả)</option>
                    <option value="200000000">Không thành vấn đề!</option>
                  </select>
                </div>

                <div>
                  <label className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700 mb-3">
                    <Filter size={18} className="text-amber-600" />
                    Hãng sản xuất yêu thích (Tùy chọn)
                  </label>
                  <select
                    value={form.filters.brandCode || ""}
                    onChange={(e) => setForm({...form, filters: {...form.filters, brandCode: e.target.value || null}})}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-4 text-base text-slate-900 outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100 transition font-medium"
                  >
                    <option value="">Tất cả các hãng (Gợi ý máy ngon nhất)</option>
                    {options.brands.map(b => (
                      <option key={b.code} value={b.code}>Chỉ xem hãng {b.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </section>

            <div className="flex justify-center mt-8 pt-4">
              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center justify-center gap-3 rounded-2xl bg-sky-600 hover:bg-sky-700 disabled:bg-sky-400 text-white px-10 py-5 text-lg font-bold transition shadow-xl shadow-sky-600/20 hover:shadow-sky-600/40 w-full sm:w-auto min-w-[300px]"
              >
                {loading ? (
                  <>
                    <Zap size={22} className="animate-pulse" />
                    Đang giải bài toán AI...
                  </>
                ) : (
                  <>
                    <Zap size={22} />
                    Tìm Laptop Chân Ái Của Tôi!
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}