import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload as UploadIcon, FileDown, FileSpreadsheet, CheckCircle, AlertTriangle, ArrowRight, Zap } from 'lucide-react';
import api from '../services/api';

const Upload = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [isRaw, setIsRaw] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      processFile(droppedFile);
    }
  };

  const processFile = (selectedFile) => {
    setFile(selectedFile);
    setValidationResult(null);
    validateFile(selectedFile);
  };

  const validateFile = async (fileToValidate) => {
    setValidating(true);
    const formData = new FormData();
    formData.append('file', fileToValidate);
    formData.append('is_raw', isRaw);

    try {
      const response = await api.post('/upload/validate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setValidationResult(response.data);
    } catch (error) {
      setValidationResult({
        is_valid: false,
        errors: [error.response?.data?.detail?.message || error.response?.data?.detail || 'Gagal validasi file']
      });
    } finally {
      setValidating(false);
    }
  };

  const handleProcess = async () => {
    if (!file || !validationResult?.is_valid) return;
    
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_raw', isRaw);

    try {
      const response = await api.post('/predict/batch', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      navigate(`/ranking/${response.data.session_id}`);
    } catch (error) {
      alert('Gagal memproses data: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/export/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Template_KIPK_Upload.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert('Gagal mendownload template');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Upload Data KIP-K</h1>
          <p className="text-slate-500 mt-1">Unggah file Excel pendaftar untuk diproses oleh Machine Learning.</p>
        </div>
        <button onClick={handleDownloadTemplate} className="btn-secondary gap-2 text-sm group">
          <FileDown size={18} className="text-slate-400 group-hover:text-primary-500 transition-colors" />
          Download Template
        </button>
      </div>

      {/* Mode Selection */}
      <div className="bg-white p-1.5 rounded-2xl shadow-sm border border-slate-200 inline-flex max-w-fit relative z-10">
        <button
          onClick={() => { setIsRaw(false); setFile(null); setValidationResult(null); }}
          className={`relative px-6 py-2.5 text-sm font-semibold rounded-xl transition-all duration-300 ${!isRaw ? 'text-primary-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
        >
          {!isRaw && <div className="absolute inset-0 bg-primary-50 rounded-xl -z-10"></div>}
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className={!isRaw ? 'text-primary-500' : 'opacity-0 hidden'} />
            Data Template (Sesuai Format)
          </div>
        </button>
        <button
          onClick={() => { setIsRaw(true); setFile(null); setValidationResult(null); }}
          className={`relative px-6 py-2.5 text-sm font-semibold rounded-xl transition-all duration-300 ${isRaw ? 'text-primary-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
        >
          {isRaw && <div className="absolute inset-0 bg-primary-50 rounded-xl -z-10"></div>}
          <div className="flex items-center gap-2">
            <Zap size={16} className={isRaw ? 'text-amber-500' : 'opacity-0 hidden'} />
            Data Mentah (Auto-ETL)
          </div>
        </button>
      </div>

      {/* Upload Dropzone */}
      <div className="card-static overflow-hidden relative group">
        {/* Animated background blob on hover */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-gradient-to-br from-primary-50 to-indigo-50/50 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none -z-10"></div>
        
        <input
          type="file"
          accept=".xlsx, .xls, .csv"
          className="hidden"
          ref={fileInputRef}
          onChange={handleFileChange}
        />
        
        <div 
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 ${
            isDragging 
              ? 'border-primary-500 bg-primary-50 scale-[1.02]' 
              : file 
                ? 'border-primary-400 bg-primary-50/50' 
                : 'border-slate-200 hover:border-primary-400 hover:bg-slate-50/50'
          }`}
        >
          <div className="mx-auto flex flex-col items-center justify-center space-y-5">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center transition-colors duration-300 ${file ? 'bg-primary-100' : 'bg-slate-100 group-hover:bg-primary-50'}`}>
              {file ? (
                <FileSpreadsheet size={40} className="text-primary-600" />
              ) : (
                <UploadIcon size={40} className="text-slate-400 group-hover:text-primary-500 transition-colors" />
              )}
            </div>
            
            <div>
              {file ? (
                <div className="animate-slide-up">
                  <p className="text-xl font-bold text-slate-800">{file.name}</p>
                  <p className="text-sm text-slate-500 mt-1">{(file.size / 1024).toFixed(2)} KB</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-lg font-bold text-slate-700">
                    Klik untuk upload atau drag & drop
                  </p>
                  <p className="text-sm text-slate-500 max-w-xs mx-auto">
                    {isRaw 
                      ? "Mendukung file Excel mentah langsung dari sistem kampus (Auto-Cleaning)." 
                      : "Gunakan file Excel yang telah disesuaikan dengan template."}
                  </p>
                </div>
              )}
            </div>
            
            {!file && (
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <span>.XLSX</span> • <span>.XLS</span> • <span>.CSV</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Validation Result */}
      {validating && (
        <div className="card p-8 text-center animate-pulse">
          <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-lg font-medium text-slate-600">Memvalidasi struktur file...</p>
          <p className="text-sm text-slate-400 mt-1">Sistem sedang memeriksa kelengkapan kolom dan format data.</p>
        </div>
      )}

      {validationResult && !validating && (
        <div className="animate-slide-up">
          {validationResult.is_valid ? (
            <div className="bg-gradient-to-br from-emerald-50 to-green-50/50 border border-emerald-200/60 rounded-3xl p-8 shadow-sm">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-emerald-100 rounded-2xl text-emerald-600 shadow-inner">
                    <CheckCircle size={28} />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-emerald-900 tracking-tight">Validasi Berhasil!</h3>
                    <p className="text-emerald-700 mt-1">
                      Ditemukan <span className="font-bold text-emerald-900">{validationResult.total_rows}</span> data mahasiswa yang valid dan siap diproses.
                    </p>
                  </div>
                </div>
                
                <button 
                  onClick={handleProcess}
                  disabled={loading}
                  className="btn-primary w-full md:w-auto px-8 py-3.5 shadow-lg shadow-emerald-500/20 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 focus:ring-emerald-500 text-lg group"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      Memproses ML...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      Mulai Proses Prediksi
                      <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                    </span>
                  )}
                </button>
              </div>
                  
              {/* Preview Table */}
              <div className="mt-8 bg-white rounded-xl border border-emerald-200 overflow-hidden shadow-sm">
                <div className="px-5 py-3 border-b border-emerald-100 bg-emerald-50 flex justify-between items-center">
                  <p className="text-xs font-bold text-emerald-800 uppercase tracking-widest">Preview Data (5 Baris)</p>
                  <span className="badge badge-green">{validationResult.columns?.length} Kolom Terdeteksi</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-emerald-100 text-sm">
                    <thead className="bg-white">
                      <tr>
                        <th className="px-5 py-3 text-left text-xs font-bold text-slate-600 uppercase">NIM</th>
                        <th className="px-5 py-3 text-left text-xs font-bold text-slate-600 uppercase">Nama</th>
                        <th className="px-5 py-3 text-left text-xs font-bold text-slate-600 uppercase">Prodi</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-emerald-50 bg-white">
                      {validationResult.preview?.slice(0,5).map((row, i) => (
                        <tr key={i} className="hover:bg-slate-50 transition-colors">
                          <td className="px-5 py-3 text-slate-700 font-mono">{row.NIM}</td>
                          <td className="px-5 py-3 font-semibold text-slate-900">{row['Nama Mahasiswa'] || row.Nama_Mahasiswa}</td>
                          <td className="px-5 py-3 text-slate-700">{row['Pilihan Prodi 1'] || row.Pilihan_Prodi_1}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-rose-50 border border-rose-200 rounded-3xl p-8 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-rose-100 rounded-2xl text-rose-600 shadow-inner shrink-0">
                  <AlertTriangle size={28} />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-rose-900 tracking-tight">Validasi Gagal</h3>
                  <p className="text-rose-700 mt-1 mb-4">Sistem menemukan masalah pada struktur data Excel Anda:</p>
                  <ul className="space-y-2">
                    {validationResult.errors?.map((err, i) => (
                      <li key={i} className="flex items-start gap-2 text-rose-600 text-sm bg-white/50 p-3 rounded-xl border border-rose-100">
                        <span className="text-rose-400 mt-0.5">•</span>
                        <span>{err}</span>
                      </li>
                    ))}
                  </ul>
                  {!isRaw && (
                    <div className="mt-6 inline-flex items-center gap-2 text-sm text-rose-700 bg-rose-100/50 px-4 py-2 rounded-lg">
                      <Zap size={16} className="text-amber-500" />
                      <span>Tips: Jika ini file dari kampus, coba gunakan mode <strong>Data Mentah (Auto-ETL)</strong></span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Upload;
