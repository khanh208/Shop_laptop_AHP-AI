import { useEffect, useState, useMemo } from 'react';
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
  ChevronRight
} from 'lucide-react';

export default function Home() {
  const [options, setOptions] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [form, setForm] = useState({
    mode: "advanced",
    usageProfile: '',
    budget: { min: 0, max: 200000000 },
    filters: {
      brandCode: null,
      cpuCode: null,
      gpuCode: null,
      minRamGb: 0,
      minSsdGb: 0,
      screenSizeMin: 0,
      screenSizeMax: 99,
      maxWeightKg: 10,
      minBatteryHours: 0
    }
  });

  useEffect(() => {
    getFormOptions()
      .then(res => {
        setOptions(res.data);
        if (res.data.usageProfiles?.length > 0) {
          setForm(prev => ({
            ...prev,
            usageProfile: res.data.usageProfiles[0].code
          }));
        }
      })
      .catch((err) => {
        console.error("Lỗi kết nối Backend!", err);
      });
  }, []);

  const availableSSDs = useMemo(() => {
    const ram = form.filters.minRamGb;

    const allSSDs = [
      { val: 0, label: "Bất kỳ dung lượng" },
      { val: 16, label: "Từ 16 GB" },
      { val: 32, label: "Từ 32 GB" },
      { val: 64, label: "Từ 64 GB" },
      { val: 128, label: "Từ 128 GB" },
      { val: 256, label: "Từ 256 GB" },
      { val: 512, label: "Từ 512 GB" },
      { val: 1000, label: "Từ 1 TB" },
      { val: 2000, label: "Từ 2 TB" }
    ];

    if (ram === 4) return allSSDs.filter(s => s.val <= 512);
    if (ram === 8) return allSSDs.filter(s => s.val <= 1000);

    if (ram === 64) {
      return allSSDs.filter(s => s.val === 0 || s.val >= 1000);
    }
    if (ram === 32) {
      return allSSDs.filter(s => s.val === 0 || s.val >= 512);
    }
    if (ram === 16) {
      return allSSDs.filter(s => s.val === 0 || s.val >= 256);
    }

    return allSSDs;
  }, [form.filters.minRamGb]);

  useEffect(() => {
    const currentSsd = form.filters.minSsdGb;
    const isValid = availableSSDs.some(s => s.val === currentSsd);

    if (!isValid) {
      setForm(prev => ({
        ...prev,
        filters: {
          ...prev.filters,
          minSsdGb: 0
        }
      }));
    }
  }, [availableSSDs, form.filters.minSsdGb]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await runRecommendation(form);
      navigate(`/dashboard/${res.data.session.sessionKey}`);
    } catch (err) {
      console.error(err);
      alert("Lỗi kết nối Backend! Hãy kiểm tra server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 px-4 py-6 md:px-8 md:py-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* HERO */}
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-sky-600 via-cyan-500 to-blue-500 text-white shadow-sm p-6 md:p-10">
          <div className="absolute -top-12 -right-10 w-48 h-48 bg-white/10 rounded-full blur-3xl"></div>
          <div className="absolute -bottom-10 left-1/3 w-56 h-56 bg-white/10 rounded-full blur-3xl"></div>

          <div className="relative z-10 grid grid-cols-1 xl:grid-cols-2 gap-8 items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs md:text-sm font-semibold uppercase tracking-wider mb-4">
                <Zap size={16} />
                Smart Hardware Validation
              </div>

              <h1 className="text-3xl sm:text-4xl md:text-5xl xl:text-6xl font-extrabold tracking-tight leading-tight">
                Laptop Selector
              </h1>

              <p className="mt-4 text-sm md:text-base xl:text-lg text-white/90 leading-7 max-w-2xl">
                Chọn nhanh cấu hình laptop phù hợp theo nhu cầu, ngân sách và các tiêu chí phần cứng quan trọng.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="rounded-2xl bg-white/15 backdrop-blur-sm border border-white/20 p-4">
                <p className="text-sm font-semibold text-white/80 mb-2">Bước 1</p>
                <p className="text-lg font-bold">Chọn nhu cầu</p>
              </div>
              <div className="rounded-2xl bg-white/15 backdrop-blur-sm border border-white/20 p-4">
                <p className="text-sm font-semibold text-white/80 mb-2">Bước 2</p>
                <p className="text-lg font-bold">Lọc cấu hình</p>
              </div>
              <div className="rounded-2xl bg-white/15 backdrop-blur-sm border border-white/20 p-4">
                <p className="text-sm font-semibold text-white/80 mb-2">Bước 3</p>
                <p className="text-lg font-bold">Xem đề xuất</p>
              </div>
            </div>
          </div>
        </section>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          {/* LEFT */}
          <div className="xl:col-span-4 space-y-6">
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-7">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-11 h-11 rounded-2xl bg-sky-100 text-sky-700 flex items-center justify-center">
                  <LayoutGrid size={20} />
                </div>
                <div>
                  <h2 className="text-xl md:text-2xl font-bold text-slate-900">Nhu cầu cơ bản</h2>
                  <p className="text-sm md:text-base text-slate-500">Thiết lập mục đích sử dụng và ngân sách</p>
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700 mb-3">
                    <Filter size={16} className="text-sky-700" />
                    Mục đích sử dụng
                  </label>
                  <select
                    value={form.usageProfile}
                    onChange={e => setForm({ ...form, usageProfile: e.target.value })}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3.5 text-base text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100 transition"
                  >
                    {options?.usageProfiles.map(p => (
                      <option key={p.code} value={p.code}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700 mb-3">
                    <Wallet size={16} className="text-sky-700" />
                    Ngân sách tối đa
                  </label>
                  <select
                    value={form.budget.max}
                    onChange={e =>
                      setForm({
                        ...form,
                        budget: {
                          ...form.budget,
                          max: parseInt(e.target.value)
                        }
                      })
                    }
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3.5 text-base text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100 transition"
                  >
                    <option value="200000000">Không giới hạn (Bất kỳ)</option>
                    <option value="15000000">Dưới 15 Triệu</option>
                    <option value="20000000">Dưới 20 Triệu</option>
                    <option value="25000000">Dưới 25 Triệu</option>
                    <option value="30000000">Dưới 30 Triệu</option>
                    <option value="40000000">Dưới 40 Triệu</option>
                  </select>
                </div>
              </div>
            </section>

            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-7">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-11 h-11 rounded-2xl bg-indigo-100 text-indigo-600 flex items-center justify-center">
                  <Filter size={20} />
                </div>
                <div>
                  <h2 className="text-xl md:text-2xl font-bold text-slate-900">Hãng sản xuất</h2>
                  <p className="text-sm md:text-base text-slate-500">Chọn thương hiệu bạn muốn ưu tiên</p>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <button
                  type="button"
                  onClick={() => setForm({ ...form, filters: { ...form.filters, brandCode: null } })}
                  className={`rounded-2xl px-4 py-4 text-sm md:text-base font-semibold border transition-all text-left ${
                    form.filters.brandCode === null
                      ? 'bg-sky-600 text-white border-sky-600 shadow-md'
                      : 'bg-white text-slate-700 border-slate-300 hover:border-sky-300 hover:bg-sky-50'
                  }`}
                >
                  <div className="font-bold">Tất cả</div>
                  <div className={`text-xs mt-1 ${form.filters.brandCode === null ? 'text-white/80' : 'text-slate-500'}`}>
                    Không giới hạn thương hiệu
                  </div>
                </button>

                {options?.brands.map((brand) => (
                  <button
                    key={brand.code}
                    type="button"
                    onClick={() =>
                      setForm({
                        ...form,
                        filters: {
                          ...form.filters,
                          brandCode: brand.code
                        }
                      })
                    }
                    className={`rounded-2xl px-4 py-4 text-sm md:text-base font-semibold border transition-all text-left ${
                      form.filters.brandCode === brand.code
                        ? 'bg-sky-600 text-white border-sky-600 shadow-md'
                        : 'bg-white text-slate-700 border-slate-300 hover:border-sky-300 hover:bg-sky-50'
                    }`}
                  >
                    <div className="font-bold truncate">{brand.name}</div>
                    <div className={`text-xs mt-1 ${form.filters.brandCode === brand.code ? 'text-white/80' : 'text-slate-500'}`}>
                      {form.filters.brandCode === brand.code ? 'Đang được ưu tiên' : 'Chọn thương hiệu này'}
                    </div>
                  </button>
                ))}
              </div>
            </section>
          </div>

          {/* RIGHT */}
          <div className="xl:col-span-8 space-y-6">
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 md:p-7">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-11 h-11 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center">
                  <CpuIcon />
                </div>
                <div>
                  <h2 className="text-xl md:text-2xl font-bold text-slate-900">Yêu cầu phần cứng</h2>
                  <p className="text-sm md:text-base text-slate-500">Tùy chỉnh bộ nhớ, màn hình, pin và trọng lượng</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
                  <h3 className="text-lg font-bold text-slate-900 mb-5">Bộ nhớ</h3>

                  <div className="space-y-5">
                    <div>
                      <label className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700 mb-3">
                        <MemoryStick size={16} className="text-sky-700" />
                        Dung lượng RAM
                      </label>
                      <select
                        value={form.filters.minRamGb}
                        onChange={e =>
                          setForm({
                            ...form,
                            filters: {
                              ...form.filters,
                              minRamGb: parseInt(e.target.value)
                            }
                          })
                        }
                        className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3.5 text-base text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100 transition"
                      >
                        <option value="0">Bất kỳ</option>
                        <option value="4">Từ 4 GB (Tối thiểu)</option>
                        <option value="8">Từ 8 GB (Cơ bản)</option>
                        <option value="16">Từ 16 GB (Khuyên dùng)</option>
                        <option value="24">Từ 24 GB (Nâng cao)</option>
                        <option value="32">Từ 32 GB (Chuyên nghiệp)</option>
                        <option value="64">Từ 64 GB (Tối đa)</option>
                      </select>
                    </div>

                    <div>
                      <label className="flex items-center justify-between gap-3 mb-3">
                        <span className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700">
                          <HardDrive size={16} className="text-sky-700" />
                          Ổ cứng SSD
                        </span>

                        {form.filters.minRamGb <= 8 && form.filters.minRamGb > 0 && (
                          <span className="rounded-full bg-amber-100 text-amber-700 px-3 py-1 text-xs md:text-sm font-semibold">
                            Giới hạn theo RAM
                          </span>
                        )}
                      </label>

                      <select
                        value={form.filters.minSsdGb}
                        onChange={e =>
                          setForm({
                            ...form,
                            filters: {
                              ...form.filters,
                              minSsdGb: parseInt(e.target.value)
                            }
                          })
                        }
                        className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3.5 text-base text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100 transition"
                      >
                        {availableSSDs.map(ssd => (
                          <option key={ssd.val} value={ssd.val}>
                            {ssd.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
                  <h3 className="text-lg font-bold text-slate-900 mb-5">Kích thước & di động</h3>

                  <div className="space-y-5">
                    <div>
                      <label className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700 mb-3">
                        <Monitor size={16} className="text-sky-700" />
                        Kích thước màn hình
                      </label>
                      <select
                        onChange={e => {
                          const [min, max] = e.target.value.split('-').map(Number);
                          setForm({
                            ...form,
                            filters: {
                              ...form.filters,
                              screenSizeMin: min,
                              screenSizeMax: max
                            }
                          });
                        }}
                        className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3.5 text-base text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100 transition"
                      >
                        <option value="0-99">Bất kỳ kích thước</option>
                        <option value="13.0-14.5">Nhỏ gọn (13" - 14.5")</option>
                        <option value="15.0-16.0">Tiêu chuẩn (15" - 16")</option>
                        <option value="16.1-99">Lớn (16" trở lên)</option>
                      </select>
                    </div>

                    <div>
                      <label className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700 mb-3">
                        <Scale size={16} className="text-sky-700" />
                        Trọng lượng
                      </label>
                      <select
                        value={form.filters.maxWeightKg}
                        onChange={e =>
                          setForm({
                            ...form,
                            filters: {
                              ...form.filters,
                              maxWeightKg: parseFloat(e.target.value)
                            }
                          })
                        }
                        className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3.5 text-base text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100 transition"
                      >
                        <option value="10">Bất kỳ</option>
                        <option value="1.5">Siêu nhẹ &lt; 1.5 Kg</option>
                        <option value="2">Vừa phải &lt; 2.0 Kg</option>
                        <option value="2.5">Phổ thông &lt; 2.5 Kg</option>
                      </select>
                    </div>

                    <div>
                      <label className="flex items-center gap-2 text-sm md:text-base font-semibold text-slate-700 mb-3">
                        <BatteryCharging size={16} className="text-sky-700" />
                        Pin tối thiểu
                      </label>
                      <select
                        value={form.filters.minBatteryHours}
                        onChange={e =>
                          setForm({
                            ...form,
                            filters: {
                              ...form.filters,
                              minBatteryHours: parseInt(e.target.value)
                            }
                          })
                        }
                        className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3.5 text-base text-slate-900 outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-100 transition"
                      >
                        <option value="0">Bất kỳ</option>
                        <option value="4">&gt; 4 giờ</option>
                        <option value="6">&gt; 6 giờ</option>
                        <option value="8">&gt; 8 giờ</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-8 rounded-3xl bg-slate-50 border border-slate-200 p-5 md:p-6 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
                <div>
                  <h3 className="text-lg md:text-xl font-bold text-slate-900">
                    Sẵn sàng tạo cấu hình đề xuất
                  </h3>
                  <p className="text-sm md:text-base text-slate-500 mt-1 leading-7">
                    Hệ thống sẽ lọc laptop theo các tiêu chí bạn đã chọn và chuyển sang trang phân tích kết quả.
                  </p>
                </div>

                <button
                  disabled={loading}
                  className="shrink-0 inline-flex items-center justify-center gap-2 rounded-2xl bg-sky-600 hover:bg-sky-700 disabled:bg-sky-400 text-white px-6 py-4 text-base md:text-lg font-semibold transition min-w-[220px]"
                >
                  {loading ? (
                    <>
                      <Zap size={18} className="animate-pulse" />
                      Đang xử lý...
                    </>
                  ) : (
                    <>
                      Kiến tạo cấu hình
                      <ChevronRight size={18} />
                    </>
                  )}
                </button>
              </div>
            </section>
          </div>
        </form>
      </div>
    </div>
  );
}

function CpuIcon() {
  return <Filter size={20} />;
}