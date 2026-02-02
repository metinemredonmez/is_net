'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { documentsService } from '@/services/documents.service';
import { useAuth } from '@/hooks/useAuth';
import type { Document, DocumentCategory, PaginatedResponse } from '@/types';
import {
  FileText,
  Search,
  Upload,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye,
  Trash2,
  RotateCcw,
  Filter,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { tr } from 'date-fns/locale';
import { toast } from 'sonner';

// Add missing Select component
import * as SelectPrimitive from '@radix-ui/react-select';

export default function DocumentsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { canUploadDocuments, isAdmin } = useAuth();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [categories, setCategories] = useState<DocumentCategory[]>([]);
  const [pagination, setPagination] = useState({
    count: 0,
    next: null as string | null,
    previous: null as string | null,
  });
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [status, setStatus] = useState(searchParams.get('status') || 'all');
  const [category, setCategory] = useState(searchParams.get('category') || 'all');
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1);

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page };
      if (search) params.search = search;
      if (status && status !== 'all') params.status = status;
      if (category && category !== 'all') params.category = category;

      const response = await documentsService.getDocuments(params);
      setDocuments(response.results);
      setPagination({
        count: response.count,
        next: response.next,
        previous: response.previous,
      });
    } catch (error) {
      console.error('Error fetching documents:', error);
      toast.error('Dokümanlar yüklenirken hata oluştu');
    } finally {
      setIsLoading(false);
    }
  }, [page, search, status, category]);

  const fetchCategories = useCallback(async () => {
    try {
      const data = await documentsService.getCategories();
      setCategories(data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchDocuments();
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Bu dokümanı silmek istediğinizden emin misiniz?')) return;

    try {
      await documentsService.deleteDocument(id);
      toast.success('Doküman silindi');
      fetchDocuments();
    } catch {
      toast.error('Silme işlemi başarısız');
    }
  };

  const handleReprocess = async (id: string) => {
    try {
      await documentsService.reprocessDocument(id);
      toast.success('Yeniden işleme başlatıldı');
      fetchDocuments();
    } catch {
      toast.error('Yeniden işleme başlatılamadı');
    }
  };

  const getStatusBadge = (docStatus: string) => {
    switch (docStatus) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-800">Tamamlandı</Badge>;
      case 'processing':
        return (
          <Badge className="bg-blue-100 text-blue-800">
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            İşleniyor
          </Badge>
        );
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">Bekliyor</Badge>;
      case 'failed':
        return <Badge className="bg-red-100 text-red-800">Başarısız</Badge>;
      default:
        return <Badge variant="outline">{docStatus}</Badge>;
    }
  };

  const getFileTypeBadge = (fileType: string) => {
    const colors: Record<string, string> = {
      pdf: 'bg-red-100 text-red-800',
      docx: 'bg-blue-100 text-blue-800',
      txt: 'bg-gray-100 text-gray-800',
      md: 'bg-purple-100 text-purple-800',
    };
    return (
      <Badge className={colors[fileType] || 'bg-gray-100 text-gray-800'}>
        {fileType.toUpperCase()}
      </Badge>
    );
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const totalPages = Math.ceil(pagination.count / 20);

  return (
    <DashboardLayout title="Dokümanlar">
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <p className="text-slate-500">
            Toplam {pagination.count} doküman
          </p>
        </div>
        {canUploadDocuments && (
          <Link href="/documents/upload">
            <Button>
              <Upload className="mr-2 h-4 w-4" />
              Yeni Doküman Yükle
            </Button>
          </Link>
        )}
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <form onSubmit={handleSearch} className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Doküman ara..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Durum" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm Durumlar</SelectItem>
                <SelectItem value="pending">Bekliyor</SelectItem>
                <SelectItem value="processing">İşleniyor</SelectItem>
                <SelectItem value="completed">Tamamlandı</SelectItem>
                <SelectItem value="failed">Başarısız</SelectItem>
              </SelectContent>
            </Select>

            <Select value={category} onValueChange={(v) => { setCategory(v); setPage(1); }}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Kategori" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm Kategoriler</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat.id} value={cat.slug}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button type="submit" variant="secondary">
              <Filter className="mr-2 h-4 w-4" />
              Filtrele
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Documents Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : documents.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="mx-auto h-12 w-12 text-slate-300 mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">
                Doküman bulunamadı
              </h3>
              <p className="text-slate-500 mb-4">
                Arama kriterlerinize uygun doküman yok.
              </p>
              {canUploadDocuments && (
                <Link href="/documents/upload">
                  <Button>İlk dokümanınızı yükleyin</Button>
                </Link>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Başlık</TableHead>
                  <TableHead>Tür</TableHead>
                  <TableHead>Boyut</TableHead>
                  <TableHead>Durum</TableHead>
                  <TableHead>Tarih</TableHead>
                  <TableHead className="text-right">İşlemler</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <Link
                        href={`/documents/${doc.id}`}
                        className="font-medium hover:text-primary"
                      >
                        {doc.title}
                      </Link>
                      {doc.is_public && (
                        <Badge variant="outline" className="ml-2 text-xs">
                          Herkese Açık
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>{getFileTypeBadge(doc.file_type)}</TableCell>
                    <TableCell className="text-slate-500">
                      {formatFileSize(doc.file_size)}
                    </TableCell>
                    <TableCell>{getStatusBadge(doc.status)}</TableCell>
                    <TableCell className="text-slate-500">
                      {formatDistanceToNow(new Date(doc.created_at), {
                        addSuffix: true,
                        locale: tr,
                      })}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Link href={`/documents/${doc.id}`}>
                          <Button variant="ghost" size="icon">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </Link>
                        {doc.status === 'failed' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleReprocess(doc.id)}
                          >
                            <RotateCcw className="h-4 w-4" />
                          </Button>
                        )}
                        {(isAdmin || doc.uploaded_by_name) && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(doc.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-sm text-slate-500">
            Sayfa {page} / {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!pagination.previous}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Önceki
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!pagination.next}
              onClick={() => setPage((p) => p + 1)}
            >
              Sonraki
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
