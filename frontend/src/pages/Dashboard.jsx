import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, CheckCircle, FileText, BarChart3, AlertCircle, TrendingUp, PieChart as PieChartIcon } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../services/api';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];
const CATEGORY_COLORS = {
  'Sangat Layak': '#10b981',
  'Layak': '#3b82f6',
  'Kurang Layak': '#f59e0b',
  'Tidak Layak': '#ef4444',
};

const StatCard = ({ title, value, icon: Icon, colorClass, subtitle }) => (
  <div className="card flex items-center gap-4 hover:shadow-md transition-shadow duration-300">
    <div className={`p-4 rounded-xl ${colorClass} shadow-lg`}>
      <Icon size={24} className="text-white" />
    </div>
    <div>
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <h3 className="text-2xl font-bold text-slate-800">{value}</h3>
      {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
    </div>
  </div>
);

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white px-4 py-3 shadow-xl rounded-xl border border-slate-200">
        <p className="font-semibold text-slate-800">{payload[0].name}</p>
        <p className="text-sm text-slate-600">{payload[0].value} mahasiswa</p>
      </div>
    );
  }
  return null;
};

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get('/dashboard/stats');
        setStats(response.data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        {[1, 2, 3].map(i => (
          <div key={i} className="animate-pulse card">
            <div className="h-4 bg-slate-200 rounded w-1/3 mb-3"></div>
            <div className="h-8 bg-slate-200 rounded w-1/4"></div>
          </div>
        ))}
      </div>
    );
  }

  const latestSession = stats?.sessions?.[0]; // Already sorted desc from DB
  const latestStats = latestSession?.stats || {};

  // Chart data for Pie
  const pieData = [
    { name: 'Sangat Layak', value: latestStats.sangat_layak || 0 },
    { name: 'Layak', value: latestStats.layak || 0 },
    { name: 'Kurang Layak', value: latestStats.kurang_layak || 0 },
    { name: 'Tidak Layak', value: latestStats.tidak_layak || 0 },
  ].filter(d => d.value > 0);

  // Bar chart data for session history
  const barData = (stats?.sessions || []).slice(0, 8).reverse().map((s, idx) => ({
    name: s.session_id,
    total: s.total || 0,
    diterima: s.stats?.diterima_model || 0,
    avgSkor: s.stats?.avg_skor || 0,
  }));

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard Seleksi KIP-K</h1>
        <p className="text-slate-500 mt-1">Ringkasan sistem pendukung keputusan KIP-K berbasis Machine Learning.</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Pendaftar"
          value={stats?.total_mahasiswa_diproses || 0}
          icon={Users}
          colorClass="bg-gradient-to-br from-blue-500 to-blue-600"
          subtitle="Keseluruhan sesi"
        />
        <StatCard
          title="Sesi Seleksi"
          value={stats?.total_sessions || 0}
          icon={FileText}
          colorClass="bg-gradient-to-br from-indigo-500 to-indigo-600"
          subtitle="Tersimpan di database"
        />
        <StatCard
          title="Rata-rata Skor"
          value={`${latestStats.avg_skor || 0}%`}
          icon={TrendingUp}
          colorClass="bg-gradient-to-br from-emerald-500 to-emerald-600"
          subtitle="Sesi terakhir"
        />
        <StatCard
          title="Diterima (Model)"
          value={latestStats.diterima_model || 0}
          icon={CheckCircle}
          colorClass="bg-gradient-to-br from-green-500 to-green-600"
          subtitle="Sesi terakhir"
        />
      </div>

      {/* Charts Row */}
      {latestSession && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pie Chart - Kategori Kelayakan */}
          <div className="card">
            <div className="flex items-center gap-2 mb-6">
              <PieChartIcon size={20} className="text-primary-500" />
              <h2 className="text-lg font-bold text-slate-800">Distribusi Kelayakan</h2>
            </div>
            <p className="text-xs text-slate-400 mb-4">Sesi terakhir: {latestSession.filename}</p>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={4}
                    dataKey="value"
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={true}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-slate-400">
                Belum ada data
              </div>
            )}
          </div>

          {/* Bar Chart - Session Comparison */}
          <div className="card">
            <div className="flex items-center gap-2 mb-6">
              <BarChart3 size={20} className="text-primary-500" />
              <h2 className="text-lg font-bold text-slate-800">Perbandingan Antar Sesi</h2>
            </div>
            <p className="text-xs text-slate-400 mb-4">8 sesi terakhir</p>
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Bar dataKey="total" name="Total Pendaftar" fill="#6366f1" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="diterima" name="Diterima" fill="#10b981" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-slate-400">
                Belum ada data
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recent Sessions Table */}
      <div className="card">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <BarChart3 size={20} className="text-primary-500" />
            Riwayat Seleksi Terbaru
          </h2>
          <Link to="/upload" className="btn-primary text-sm">
            Mulai Seleksi Baru
          </Link>
        </div>
        
        {stats?.sessions?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-500 uppercase bg-slate-50">
                <tr>
                  <th className="px-6 py-3 rounded-tl-lg">ID Sesi</th>
                  <th className="px-6 py-3">Tanggal</th>
                  <th className="px-6 py-3">File</th>
                  <th className="px-6 py-3">Total Data</th>
                  <th className="px-6 py-3">Diterima</th>
                  <th className="px-6 py-3">Kuota</th>
                  <th className="px-6 py-3 rounded-tr-lg">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {stats.sessions.slice(0, 10).map((session) => (
                  <tr key={session.session_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-mono font-medium text-slate-900">{session.session_id}</td>
                    <td className="px-6 py-4 text-slate-500">{new Date(session.created_at).toLocaleString('id-ID')}</td>
                    <td className="px-6 py-4 text-slate-500 max-w-[200px] truncate" title={session.filename}>{session.filename}</td>
                    <td className="px-6 py-4">{session.total} Mahasiswa</td>
                    <td className="px-6 py-4">
                      <span className="bg-green-100 text-green-800 py-1 px-2 rounded-full text-xs font-medium">
                        {session.stats?.diterima_model || 0}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {session.kuota ? (
                         <span className="bg-primary-100 text-primary-800 py-1 px-2 rounded-full text-xs font-medium">
                           {session.kuota}
                         </span>
                      ) : (
                        <span className="text-slate-400 italic">Belum diset</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <Link to={`/ranking/${session.session_id}`} className="text-primary-600 hover:text-primary-800 font-medium hover:underline">
                        Lihat Hasil &rarr;
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-10 bg-slate-50 rounded-lg border border-dashed border-slate-300">
            <FileText size={48} className="mx-auto text-slate-300 mb-3" />
            <p className="text-slate-500">Belum ada data seleksi. Silakan upload file data KIP-K.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
