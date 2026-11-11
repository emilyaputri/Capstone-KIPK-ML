import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, TrendingUp, TrendingDown, Info, ShieldAlert, CheckCircle, XCircle, Calculator } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import api from '../services/api';

const Detail = () => {
  const { sessionId, nim } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [overrideKeputusan, setOverrideKeputusan] = useState('');
  const [overrideAlasan, setOverrideAlasan] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchDetail();
  }, [sessionId, nim]);

  const fetchDetail = async () => {
    try {
      const response = await api.get(`/predict/result/${sessionId}/${nim}`);
      setData(response.data);
      setOverrideKeputusan(response.data.keputusan_final || response.data.prediksi);
      setOverrideAlasan(response.data.alasan_override || '');
    } catch (error) {
      alert('Gagal mengambil data detail mahasiswa');
    } finally {
      setLoading(false);
    }
  };

  const handleOverride = async () => {
    if (!overrideAlasan && overrideKeputusan !== data.prediksi) {
      alert('Alasan wajib diisi jika mengubah keputusan rekomendasi ML');
      return;
    }
    
    setSubmitting(true);
    try {
      await api.put(`/predict/result/${sessionId}/${nim}/override?keputusan=${overrideKeputusan}&alasan=${encodeURIComponent(overrideAlasan)}`);
      alert('Keputusan berhasil disimpan');
      fetchDetail();
    } catch (error) {
      alert('Gagal menyimpan keputusan');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
      <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
      <p className="text-slate-500 font-medium">Memuat detail analitik AI...</p>
    </div>
  );
  
  if (!data) return <div className="p-8 text-center text-red-500 card">Data tidak ditemukan</div>;

  // Format data for Recharts
  const chartData = data.shap_factors.map(f => ({
    name: f.feature,
    label: f.label.length > 30 ? f.label.substring(0, 30) + '...' : f.label,
    value: f.shap_value,
    abs: Math.abs(f.shap_value),
    direction: f.direction
  })).sort((a, b) => a.value - b.value); // Sort for horizontal bar chart

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const isPositive = data.direction === 'positif';
      return (
        <div className="bg-slate-900 text-white px-4 py-3 shadow-xl rounded-xl border border-slate-700 max-w-xs">
          <p className="font-semibold text-sm mb-1">{data.name}</p>
          <p className="text-xs text-slate-300 mb-2">{data.label}</p>
          <div className={`flex items-center gap-1.5 font-bold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            Dampak: {data.value > 0 ? '+' : ''}{data.value.toFixed(4)}
          </div>
        </div>
      );
    }
    return null;
  };

  const finalStatus = data.keputusan_final || data.prediksi;
  const isLulus = finalStatus === "Diterima";

  return (
    <div className="space-y-6 max-w-6xl mx-auto animate-fade-in pb-12">
      <button 
        onClick={() => navigate(`/ranking/${sessionId}`)} 
        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 hover:text-slate-900 transition-all shadow-sm"
      >
        <ArrowLeft size={16} /> Kembali ke Tabel Ranking
      </button>

      {/* Header Profile Info */}
      <div className="relative overflow-hidden rounded-3xl bg-white border border-slate-200 shadow-card">
        {/* Background gradient banner */}
        <div className={`h-24 w-full bg-gradient-to-r ${isLulus ? 'from-emerald-500 to-teal-400' : 'from-rose-500 to-orange-400'}`}></div>
        
        <div className="px-8 pb-8 pt-0 flex flex-col md:flex-row md:items-end justify-between gap-6 relative z-10">
          <div className="flex flex-col md:flex-row md:items-end gap-6 -mt-10">
            <div className="w-24 h-24 rounded-2xl bg-white shadow-lg p-1.5 shrink-0 flex items-center justify-center">
              <div className="w-full h-full rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-300">
                <User size={48} />
              </div>
            </div>
            
            <div className="mb-1">
              <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">{data.nama}</h1>
              <p className="text-slate-500 font-mono mt-0.5 flex items-center gap-2">
                {data.nim}
                <span className="inline-block w-1 h-1 rounded-full bg-slate-300"></span>
                <span className="text-sm font-medium">Rank #{data.rank}</span>
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 bg-slate-50 p-2 rounded-2xl border border-slate-100 mt-4 md:mt-0">
            <div className="px-5 py-3 rounded-xl bg-white shadow-sm border border-slate-100 text-center min-w-[120px]">
              <p className="text-[10px] uppercase tracking-widest font-bold text-slate-400 mb-1">Skor Model</p>
              <div className="flex items-center justify-center gap-2">
                <span className="text-2xl font-black text-slate-800">{data.skor}%</span>
              </div>
            </div>
            <div className={`px-5 py-3 rounded-xl shadow-sm border text-center min-w-[120px] ${
              isLulus ? 'bg-emerald-50 border-emerald-100' : 'bg-rose-50 border-rose-100'
            }`}>
              <p className={`text-[10px] uppercase tracking-widest font-bold mb-1 ${isLulus ? 'text-emerald-600/70' : 'text-rose-600/70'}`}>Status Final</p>
              <div className={`flex items-center justify-center gap-1.5 text-lg font-bold ${isLulus ? 'text-emerald-700' : 'text-rose-700'}`}>
                {isLulus ? <CheckCircle size={18} /> : <XCircle size={18} />}
                {finalStatus}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SHAP Explanation - 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card-static">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
                <Calculator size={20} className="text-primary-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-800">Analisis SHAP (Explainable AI)</h2>
                <p className="text-sm text-slate-500">Membongkar faktor dominan dari keputusan Machine Learning.</p>
              </div>
            </div>
            
            <div className="h-96 w-full mt-8">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={chartData}
                  margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={true} stroke="#f1f5f9" />
                  <XAxis type="number" tick={{fontSize: 12, fill: '#94a3b8'}} />
                  <YAxis dataKey="label" type="category" width={180} tick={{fontSize: 11, fill: '#475569'}} axisLine={false} tickLine={false} />
                  <RechartsTooltip content={<CustomTooltip />} cursor={{fill: '#f8fafc'}} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.direction === 'positif' ? '#10b981' : '#f43f5e'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-slate-100 text-xs font-medium text-slate-500">
              <span className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-emerald-500"></div> Mendukung Kelulusan
              </span>
              <span className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-rose-500"></div> Mengurangi Kelulusan
              </span>
            </div>
          </div>
          
          <div className="card-static bg-primary-50/30 border-primary-100">
            <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
              <Info size={18} className="text-primary-500" />
              Kesimpulan Naratif
            </h3>
            <div className="text-sm text-slate-700 whitespace-pre-line leading-relaxed">
              {data.narrative}
            </div>
          </div>
        </div>

        {/* Data & Override - 1 column */}
        <div className="space-y-6">
          <div className="card-static">
            <h2 className="text-lg font-bold text-slate-800 mb-5">Data Pendaftar Asli</h2>
            <div className="space-y-3.5">
              {Object.entries(data.data_asli).map(([key, value]) => {
                if (key.includes('prodi')) return null; // Skip prodi
                return (
                  <div key={key} className="flex justify-between items-start border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                    <span className="text-xs text-slate-500 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="text-sm font-semibold text-slate-900 text-right max-w-[60%]">
                      {typeof value === 'number' && key.includes('penghasilan') 
                        ? `Rp ${value.toLocaleString('id-ID')}` 
                        : value || '-'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card-static border-orange-200 bg-orange-50/30 relative overflow-hidden">
            {/* Warning strip */}
            <div className="absolute top-0 left-0 w-1.5 h-full bg-orange-400"></div>
            
            <h2 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2">
              <ShieldAlert size={20} className="text-orange-500" />
              Intervensi Admin
            </h2>
            <p className="text-xs text-slate-500 mb-5 leading-relaxed">
              Machine Learning hanya berfungsi sebagai Decision Support System (DSS). Admin memiliki otoritas penuh untuk membatalkan rekomendasi sistem.
            </p>
            
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Keputusan Final</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setOverrideKeputusan('Diterima')}
                    className={`py-2.5 rounded-xl text-sm font-bold border-2 transition-all ${
                      overrideKeputusan === 'Diterima' 
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-700' 
                        : 'border-slate-200 bg-white text-slate-500 hover:border-emerald-200 hover:bg-emerald-50/50'
                    }`}
                  >
                    LULUS KIP-K
                  </button>
                  <button
                    onClick={() => setOverrideKeputusan('Tidak Diterima')}
                    className={`py-2.5 rounded-xl text-sm font-bold border-2 transition-all ${
                      overrideKeputusan === 'Tidak Diterima' 
                        ? 'border-rose-500 bg-rose-50 text-rose-700' 
                        : 'border-slate-200 bg-white text-slate-500 hover:border-rose-200 hover:bg-rose-50/50'
                    }`}
                  >
                    TOLAK
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Catatan Reviewer <span className="text-rose-500">*</span>
                </label>
                <textarea 
                  className="input-field p-3 text-sm min-h-[100px] resize-none"
                  placeholder="Wajib diisi jika Anda mengubah rekomendasi dari ML. Contoh: Verifikasi lapangan menemukan rumah tidak sesuai data."
                  value={overrideAlasan}
                  onChange={(e) => setOverrideAlasan(e.target.value)}
                ></textarea>
              </div>
              
              <button 
                onClick={handleOverride}
                disabled={submitting || (overrideKeputusan === (data.keputusan_final || data.prediksi) && !overrideAlasan)}
                className="w-full btn-primary bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 shadow-orange-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Menyimpan...
                  </div>
                ) : 'Konfirmasi Keputusan'}
              </button>

              {data.alasan_override && overrideKeputusan === data.keputusan_final && (
                <div className="mt-4 p-3 bg-white/60 border border-orange-100 rounded-xl">
                  <p className="text-[10px] font-bold text-orange-500 uppercase tracking-wider mb-1">Riwayat Override</p>
                  <p className="text-xs text-slate-600 italic">"{data.alasan_override}"</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Detail;
