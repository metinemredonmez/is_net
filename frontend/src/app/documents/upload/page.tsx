'use client';

import { useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { documentsService } from '@/services/documents.service';
import { useAuth } from '@/hooks/useAuth';
import type { DocumentCategory } from '@/types';
import {
  Upload,
  FileText,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  CloudUpload,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useEffect } from 'react';

interface FileUpload {
  file: File;
  title: string;
  description: string;
  category_id: string;
  is_public: boolean;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
];

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md'];

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

export default function DocumentUploadPage() {
  const router = useRouter();
  const { canUploadDocuments } = useAuth({ required: true });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [files, setFiles] = useState<FileUpload[]>([]);
  const [categories, setCategories] = useState<DocumentCategory[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const data = await documentsService.getCategories();
        setCategories(data);
      } catch (error) {
        console.error('Error fetching categories:', error);
      }
    };
    fetchCategories();
  }, []);

  const validateFile = (file: File): string | null => {
    // Check file type
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Desteklenmeyen dosya türü. İzin verilen: ${ALLOWED_EXTENSIONS.join(', ')}`;
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return `Dosya boyutu çok büyük. Maksimum: 50MB`;
    }

    return null;
  };

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const filesToAdd: FileUpload[] = [];

    Array.from(newFiles).forEach((file) => {
      // Check if file already added
      if (files.some((f) => f.file.name === file.name)) {
        toast.error(`${file.name} zaten eklenmiş`);
        return;
      }

      const error = validateFile(file);
      if (error) {
        toast.error(`${file.name}: ${error}`);
        return;
      }

      filesToAdd.push({
        file,
        title: file.name.replace(/\.[^/.]+$/, ''), // Remove extension
        description: '',
        category_id: '',
        is_public: false,
        progress: 0,
        status: 'pending',
      });
    });

    if (filesToAdd.length > 0) {
      setFiles((prev) => [...prev, ...filesToAdd]);
    }
  }, [files]);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const updateFile = (index: number, updates: Partial<FileUpload>) => {
    setFiles((prev) =>
      prev.map((f, i) => (i === index ? { ...f, ...updates } : f))
    );
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(e.target.files);
    }
  };

  const uploadFile = async (index: number): Promise<boolean> => {
    const fileUpload = files[index];

    if (!fileUpload.title.trim()) {
      updateFile(index, { status: 'error', error: 'Başlık gerekli' });
      return false;
    }

    updateFile(index, { status: 'uploading', progress: 0 });

    try {
      // Simulate progress (actual progress would need XHR or fetch with progress)
      const progressInterval = setInterval(() => {
        setFiles((prev) =>
          prev.map((f, i) =>
            i === index && f.status === 'uploading' && f.progress < 90
              ? { ...f, progress: f.progress + 10 }
              : f
          )
        );
      }, 200);

      await documentsService.uploadDocument({
        title: fileUpload.title,
        description: fileUpload.description,
        file: fileUpload.file,
        category_id: fileUpload.category_id || undefined,
        is_public: fileUpload.is_public,
      });

      clearInterval(progressInterval);
      updateFile(index, { status: 'success', progress: 100 });
      return true;
    } catch (error: unknown) {
      const errorMessage =
        (error as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'Yükleme başarısız';
      updateFile(index, { status: 'error', error: errorMessage });
      return false;
    }
  };

  const handleUploadAll = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    if (pendingFiles.length === 0) {
      toast.error('Yüklenecek dosya yok');
      return;
    }

    setIsUploading(true);
    let successCount = 0;

    for (let i = 0; i < files.length; i++) {
      if (files[i].status === 'pending') {
        const success = await uploadFile(i);
        if (success) successCount++;
      }
    }

    setIsUploading(false);

    if (successCount > 0) {
      toast.success(`${successCount} dosya başarıyla yüklendi`);
    }

    // Redirect if all files uploaded
    if (successCount === pendingFiles.length) {
      setTimeout(() => {
        router.push('/documents');
      }, 1500);
    }
  };

  const getFileIcon = (status: FileUpload['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'uploading':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <FileText className="h-5 w-5 text-slate-400" />;
    }
  };

  if (!canUploadDocuments) {
    return (
      <DashboardLayout title="Doküman Yükle">
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="mx-auto h-12 w-12 text-yellow-500 mb-4" />
            <h3 className="text-lg font-medium mb-2">Yetkiniz Yok</h3>
            <p className="text-slate-500">
              Doküman yükleme yetkiniz bulunmamaktadır.
            </p>
          </CardContent>
        </Card>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Doküman Yükle">
      {/* Drop Zone */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              'border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors',
              isDragging
                ? 'border-primary bg-primary/5'
                : 'border-slate-200 hover:border-slate-300'
            )}
          >
            <CloudUpload
              className={cn(
                'mx-auto h-12 w-12 mb-4',
                isDragging ? 'text-primary' : 'text-slate-400'
              )}
            />
            <h3 className="text-lg font-medium mb-2">
              Dosyaları sürükleyip bırakın
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              veya dosya seçmek için tıklayın
            </p>
            <p className="text-xs text-slate-400">
              Desteklenen formatlar: PDF, DOCX, TXT, MD (Maksimum 50MB)
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ALLOWED_EXTENSIONS.join(',')}
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        </CardContent>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Yüklenecek Dosyalar ({files.length})</CardTitle>
            <Button
              onClick={handleUploadAll}
              disabled={isUploading || files.every((f) => f.status !== 'pending')}
            >
              {isUploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Yükleniyor...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Tümünü Yükle
                </>
              )}
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {files.map((fileUpload, index) => (
              <div
                key={index}
                className={cn(
                  'border rounded-lg p-4',
                  fileUpload.status === 'error' && 'border-red-200 bg-red-50',
                  fileUpload.status === 'success' && 'border-green-200 bg-green-50'
                )}
              >
                <div className="flex items-start gap-4">
                  <div className="pt-1">{getFileIcon(fileUpload.status)}</div>

                  <div className="flex-1 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{fileUpload.file.name}</p>
                        <p className="text-xs text-slate-500">
                          {(fileUpload.file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                      {fileUpload.status === 'pending' && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeFile(index)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>

                    {fileUpload.status === 'pending' && (
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div>
                          <Label htmlFor={`title-${index}`}>Başlık *</Label>
                          <Input
                            id={`title-${index}`}
                            value={fileUpload.title}
                            onChange={(e) =>
                              updateFile(index, { title: e.target.value })
                            }
                            placeholder="Doküman başlığı"
                          />
                        </div>
                        <div>
                          <Label htmlFor={`category-${index}`}>Kategori</Label>
                          <Select
                            value={fileUpload.category_id}
                            onValueChange={(v) =>
                              updateFile(index, { category_id: v })
                            }
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Kategori seçin" />
                            </SelectTrigger>
                            <SelectContent>
                              {categories.map((cat) => (
                                <SelectItem key={cat.id} value={cat.id}>
                                  {cat.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="sm:col-span-2">
                          <Label htmlFor={`desc-${index}`}>Açıklama</Label>
                          <Input
                            id={`desc-${index}`}
                            value={fileUpload.description}
                            onChange={(e) =>
                              updateFile(index, { description: e.target.value })
                            }
                            placeholder="Opsiyonel açıklama"
                          />
                        </div>
                      </div>
                    )}

                    {fileUpload.status === 'uploading' && (
                      <Progress value={fileUpload.progress} className="h-2" />
                    )}

                    {fileUpload.status === 'error' && (
                      <p className="text-sm text-red-600">{fileUpload.error}</p>
                    )}

                    {fileUpload.status === 'success' && (
                      <Badge className="bg-green-100 text-green-800">
                        <CheckCircle2 className="mr-1 h-3 w-3" />
                        Yüklendi
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </DashboardLayout>
  );
}
