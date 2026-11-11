import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Download, Users, CheckCircle, Search, Filter, AlertCircle, ArrowRight, XCircle } from 'lucide-react';
import api from '../services/api';

const Ranking = () => {
  const { sessionId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [kuota, setKuota] = useState('');
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('Semua');

  useEffect(() => {
    fetchResult();
  }, [sessionId]);

  const fetchResult = async () => {
    try {
      const response = await api.get(`/predict/result/${sessionId}`);
      setData(response.data);
      if (response.data.kuota) setKuota(response.data.kuota.toString());
    } catch (error) {
      alert('Gagal mengambil data hasil seleksi');
    } finally {
      setLoading(false);
    }
  };

  const handleSetKuota = async () => {
    if (!kuota || isNaN(kuota)) return;
    try {
      await api.post(`/predict/result/${sessionId}/kuota?kuota=${kuota}`);
      fetchResult(); // refresh data
    } catch (error) {
      alert('Gagal mengatur kuota');
    }
  };

  const handleExportExcel = async () => {
    try {
      const response = await api.get(`/export/${sessionId}/excel`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Hasil_KIPK_${sessionId}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert('Gagal mendownload Excel');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between">
          <div className="h-8 bg-slate-200 rounded w-64 animate-pulse"></div>
          <div className="h-10 bg-slate-200 rounded w-32 animate-pulse"></div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-24 bg-slate-200 rounded-2xl animate-pulse"></div>)}
        </div>
        <div className="h-96 bg-slate-200 rounded-2xl animate-pulse"></div>
      </div>
    );
  }

  if (!data) return <div className="p-12 text-center text-red-500 card">Data tidak ditemukan</div>;

  const filteredResults = data.results.filter(r => {
    const matchesSearch = r.nama.toLowerCase().includes(search.toLowerCase()) || r.nim.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'Semua' || r.kategori === filter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Hasil Seleksi ML</h1>
          <div className="flex items-center gap-3 mt-1.5">
            <span className="badge badge-indigo">Sesi: {sessionId}</span>
            <span className="text-sm text-slate-500">
              {new Date(data.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' })}
            </span>
          </div>
        </div>
        <button onClick={handleExportExcel} className="btn-secondary gap-2 text-sm shadow-sm">
          <Download size={18} className="text-primary-600" /> Export Excel
        </button>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        <div className="card-static border-l-4 border-slate-800 p-5">
          <div className="flex items-center gap-2 text-slate-500 mb-2">
            <Users size={16} />
            <span className="text-xs font-bold uppercase tracking-wider">Total Pendaftar</span>
          </div>
          <span className="text-3xl font-black text-slate-900">{data.total_mahasiswa}</span>
        </div>
        <div className="card-static border-l-4 border-emerald-500 p-5 bg-emerald-50/30">
          <div className="flex items-center gap-2 text-emerald-600 mb-2">
            <CheckCircle size={16} />
            <span className="text-xs font-bold uppercase tracking-wider">Sangat Layak</span>
          </div>
          <span className="text-3xl font-black text-emerald-700">{data.stats.sangat_layak}</span>
        </div>
        <div className="card-static border-l-4 border-blue-500 p-5 bg-blue-50/30">
          <div className="flex items-center gap-2 text-blue-600 mb-2">
            <CheckCircle size={16} />
            <span className="text-xs font-bold uppercase tracking-wider">Layak</span>
          </div>
          <span className="text-3xl font-black text-blue-700">{data.stats.layak}</span>
        </div>
        <div className="card-static border-l-4 border-rose-500 p-5 bg-rose-50/30">
          <div className="flex items-center gap-2 text-rose-600 mb-2">
            <AlertCircle size={16} />
            <span className="text-xs font-bold uppercase tracking-wider">Tidak Layak</span>
          </div>
          <span className="text-3xl font-black text-rose-700">{data.stats.tidak_layak}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Kuota Input */}
        <div className="flex items-center gap-3 w-full md:w-auto bg-slate-50 p-2 pl-4 rounded-xl border border-slate-100">
          <label className="text-sm font-semibold text-slate-700 whitespace-nowrap">Set Kuota Kelulusan:</label>
          <input 
            type="number" 
            className="w-20 px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-sm font-bold text-center focus:outline-none focus:ring-2 focus:ring-primary-500" 
            placeholder="0"
            value={kuota}
            onChange={e => setKuota(e.target.value)}
          />
          <button onClick={handleSetKuota} className="btn-primary py-1.5 px-4 text-xs">Terapkan</button>
        </div>
        
        {/* Filters */}
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
          <div className="relative w-full sm:w-64">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
              <Search size={16} className="text-slate-400" />
            </div>
            <input 
              type="text" 
              className="block w-full rounded-xl border-slate-200 bg-slate-50 pl-10 pr-4 py-2.5 text-sm focus:bg-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-colors" 
              placeholder="Cari NIM atau Nama..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          
          <select 
            className="block w-full sm:w-auto rounded-xl border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700 focus:bg-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            value={filter}
            onChange={e => setFilter(e.target.value)}
          >
            <option value="Semua">Semua Kategori</option>
            <option value="Sangat Layak">Sangat Layak</option>
            <option value="Layak">Layak</option>
            <option value="Kurang Layak">Kurang Layak</option>
            <option value="Tidak Layak">Tidak Layak</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-card border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-slate-500 uppercase tracking-wider bg-slate-50/80 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 font-bold text-center w-20">Rank</th>
                <th className="px-6 py-4 font-bold">Identitas Pendaftar</th>
                <th className="px-6 py-4 font-bold">Skor Kelayakan</th>
                <th className="px-6 py-4 font-bold">Status ML</th>
                <th className="px-6 py-4 font-bold text-center">Keputusan Akhir</th>
                <th className="px-6 py-4 font-bold"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredResults.map((r, index) => {
                const isDalamKuota = data.kuota && r.rank <= data.kuota;
                const hasOverride = r.keputusan_final !== null;
                const finalStatus = r.keputusan_final || r.prediksi;
                const isLulus = finalStatus === "Diterima";

                return (
                  <tr 
                    key={r.nim} 
                    className={`group transition-colors ${
                      isDalamKuota ? 'bg-emerald-50/30 hover:bg-emerald-50/80' : 'hover:bg-slate-50'
                    }`}
                  >
                    {/* Rank */}
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                        r.rank <= 3 ? 'bg-amber-100 text-amber-700 ring-2 ring-amber-200' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {r.rank}
                      </span>
                    </td>
                    
                    {/* Identitas */}
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-bold text-slate-900 group-hover:text-primary-600 transition-colors">{r.nama}</span>
                        <span className="text-xs font-mono text-slate-500">{r.nim}</span>
                      </div>
                    </td>

                    {/* Skor Bar */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-slate-700 w-12 text-right">{r.skor}%</span>
                        <div className="w-24 bg-slate-100 rounded-full h-2.5 overflow-hidden ring-1 ring-inset ring-slate-200/50">
                          <div 
                            className={`h-full rounded-full transition-all duration-1000 ${
                              r.skor >= 75 ? 'bg-emerald-500' : r.skor >= 50 ? 'bg-blue-500' : r.skor >= 25 ? 'bg-amber-500' : 'bg-rose-500'
                            }`} 
                            style={{ width: `${r.skor}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Kategori ML */}
                    <td className="px-6 py-4">
                      <span className={`badge ${
                        r.kategori === 'Sangat Layak' ? 'badge-green' :
                        r.kategori === 'Layak' ? 'badge-blue' :
                        r.kategori === 'Kurang Layak' ? 'badge-amber' :
                        'badge-red'
                      }`}>
                        {r.kategori}
                      </span>
                    </td>

                    {/* Final Status */}
                    <td className="px-6 py-4 text-center">
                      <div className="flex flex-col items-center">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold ${
                          isLulus ? 'text-emerald-700 bg-emerald-100/50' : 'text-rose-700 bg-rose-100/50'
                        }`}>
                          {isLulus ? <CheckCircle size={14} /> : <XCircle size={14} />}
                          {finalStatus}
                        </span>
                        {hasOverride && (
                          <span className="text-[10px] text-amber-600 font-medium mt-1 uppercase tracking-wide">Diubah Admin</span>
                        )}
                        {!hasOverride && data.kuota > 0 && (
                          <span className={`text-[10px] font-medium mt-1 uppercase tracking-wide ${isDalamKuota ? 'text-emerald-600' : 'text-slate-400'}`}>
                            {isDalamKuota ? 'Masuk Kuota' : 'Luar Kuota'}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Action */}
                    <td className="px-6 py-4 text-right">
                      <Link 
                        to={`/detail/${sessionId}/${r.nim}`}
                        className="inline-flex items-center justify-center p-2 rounded-lg text-slate-400 hover:text-primary-600 hover:bg-primary-50 transition-colors"
                        title="Lihat Detail SHAP"
                      >
                        <ArrowRight size={20} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          
          {filteredResults.length === 0 && (
            <div className="p-12 text-center">
              <Search size={40} className="mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500 font-medium">Tidak ada data yang cocok dengan kriteria pencarian.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Ranking;
