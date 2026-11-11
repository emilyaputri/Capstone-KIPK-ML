import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Download, Trash2, Eye, Calendar, Users, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import api from '../services/api';

const History = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const response = await api.get('/predict/sessions');
      setSessions(response.data);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleDelete = async (sessionId) => {
    if (!window.confirm(`Yakin ingin menghapus sesi "${sessionId}" beserta seluruh data prediksinya?`)) return;

    setDeleting(sessionId);
    try {
      await api.delete(`/predict/session/${sessionId}`);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
    } catch (error) {
      alert('Gagal menghapus sesi: ' + (error.response?.data?.detail || error.message));
    } finally {
      setDeleting(null);
    }
  };

  const handleExportExcel = (sessionId) => {
    window.open(`${api.defaults.baseURL}/export/${sessionId}/excel`, '_blank');
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <div className="h-6 bg-slate-200 rounded w-48 animate-pulse"></div>
            <div className="h-4 bg-slate-200 rounded w-72 mt-2 animate-pulse"></div>
          </div>
        </div>
        {[1, 2, 3].map(i => (
          <div key={i} className="card animate-pulse">
            <div className="h-4 bg-slate-200 rounded w-1/3 mb-3"></div>
            <div className="h-3 bg-slate-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FileText size={24} className="text-primary-500" />
            Riwayat Seleksi
          </h1>
          <p className="text-slate-500 mt-1">
            {sessions.length} sesi tersimpan di database. Data bersifat permanen.
          </p>
        </div>
        <button onClick={fetchSessions} className="btn-secondary gap-2 text-sm">
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="card text-center py-16">
          <FileText size={56} className="mx-auto text-slate-300 mb-4" />
          <h3 className="text-lg font-semibold text-slate-600">Belum Ada Riwayat</h3>
          <p className="text-slate-400 mt-1 mb-6">Mulai upload data KIP-K untuk memulai seleksi.</p>
          <Link to="/upload" className="btn-primary">Upload Data Baru</Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {sessions.map((session) => {
            const stats = session.stats || {};
            const isDeleting = deleting === session.session_id;

            return (
              <div key={session.session_id} className={`card hover:shadow-md transition-all duration-300 ${isDeleting ? 'opacity-50' : ''}`}>
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Left: Session Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="font-mono text-lg font-bold text-primary-600">
                        #{session.session_id}
                      </span>
                      {session.kuota && (
                        <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full font-medium">
                          Kuota: {session.kuota}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-500 truncate flex items-center gap-2" title={session.filename}>
                      <FileText size={14} />
                      {session.filename}
                    </p>
                    <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                      <Calendar size={12} />
                      {new Date(session.created_at).toLocaleString('id-ID', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>

                  {/* Middle: Quick Stats */}
                  <div className="flex items-center gap-6 flex-shrink-0">
                    <div className="text-center">
                      <div className="flex items-center gap-1 text-slate-500">
                        <Users size={14} />
                        <span className="text-xs">Total</span>
                      </div>
                      <p className="font-bold text-slate-800">{session.total_mahasiswa}</p>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center gap-1 text-green-600">
                        <CheckCircle size={14} />
                        <span className="text-xs">Diterima</span>
                      </div>
                      <p className="font-bold text-green-700">{stats.diterima_model || 0}</p>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center gap-1 text-red-500">
                        <XCircle size={14} />
                        <span className="text-xs">Ditolak</span>
                      </div>
                      <p className="font-bold text-red-600">{(session.total_mahasiswa || 0) - (stats.diterima_model || 0)}</p>
                    </div>
                    <div className="text-center">
                      <span className="text-xs text-slate-400">Avg Skor</span>
                      <p className="font-bold text-indigo-600">{stats.avg_skor || 0}%</p>
                    </div>
                  </div>

                  {/* Right: Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Link
                      to={`/ranking/${session.session_id}`}
                      className="btn-primary text-sm gap-1.5"
                    >
                      <Eye size={15} />
                      Lihat Hasil
                    </Link>
                    <button
                      onClick={() => handleExportExcel(session.session_id)}
                      className="btn-secondary text-sm gap-1.5"
                      title="Download Excel"
                    >
                      <Download size={15} />
                    </button>
                    <button
                      onClick={() => handleDelete(session.session_id)}
                      disabled={isDeleting}
                      className="inline-flex items-center justify-center px-3 py-2 text-sm font-medium rounded-lg text-red-600 border border-red-200 hover:bg-red-50 transition-colors disabled:opacity-50"
                      title="Hapus Sesi"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>

                {/* Stats Bar */}
                {stats.total > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-100">
                    <div className="flex gap-1 h-2.5 rounded-full overflow-hidden bg-slate-100">
                      {stats.sangat_layak > 0 && (
                        <div
                          className="bg-emerald-500 rounded-l-full transition-all"
                          style={{ width: `${(stats.sangat_layak / stats.total) * 100}%` }}
                          title={`Sangat Layak: ${stats.sangat_layak}`}
                        />
                      )}
                      {stats.layak > 0 && (
                        <div
                          className="bg-blue-500 transition-all"
                          style={{ width: `${(stats.layak / stats.total) * 100}%` }}
                          title={`Layak: ${stats.layak}`}
                        />
                      )}
                      {stats.kurang_layak > 0 && (
                        <div
                          className="bg-amber-400 transition-all"
                          style={{ width: `${(stats.kurang_layak / stats.total) * 100}%` }}
                          title={`Kurang Layak: ${stats.kurang_layak}`}
                        />
                      )}
                      {stats.tidak_layak > 0 && (
                        <div
                          className="bg-red-500 rounded-r-full transition-all"
                          style={{ width: `${(stats.tidak_layak / stats.total) * 100}%` }}
                          title={`Tidak Layak: ${stats.tidak_layak}`}
                        />
                      )}
                    </div>
                    <div className="flex gap-4 mt-2 text-xs text-slate-500">
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Sangat Layak ({stats.sangat_layak || 0})</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Layak ({stats.layak || 0})</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400"></span> Kurang Layak ({stats.kurang_layak || 0})</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span> Tidak Layak ({stats.tidak_layak || 0})</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default History;
