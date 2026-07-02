'use client';
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { clsx } from 'clsx';
import { Image as ImageIcon, Upload, X } from 'lucide-react';

interface ImageUploadProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  maxFiles?: number;
  className?: string;
}

export function ImageUpload({
  files,
  onFilesChange,
  maxFiles = 10,
  className,
}: ImageUploadProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      const combined = [...files, ...accepted].slice(0, maxFiles);
      onFilesChange(combined);
    },
    [files, onFilesChange, maxFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.heic'],
      'video/*': ['.mp4', '.mov'],
    },
    maxFiles,
    maxSize: 20 * 1024 * 1024, // 20MB
  });

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div className={clsx('space-y-3', className)}>
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-accent-500 bg-accent-500/10'
            : 'border-slate-600 hover:border-slate-500 bg-slate-800/30 hover:bg-slate-800/50'
        )}
      >
        <input {...getInputProps()} />
        <Upload
          size={36}
          className={clsx(
            'mx-auto mb-3',
            isDragActive ? 'text-accent-400' : 'text-slate-500'
          )}
        />
        <p className="text-sm font-medium text-slate-300">
          {isDragActive ? 'Drop files here' : 'Drag photos here or click to select'}
        </p>
        <p className="text-xs text-slate-500 mt-1">
          JPEG, PNG, WebP, HEIC, MP4, MOV — up to 20MB each, max {maxFiles} files
        </p>
        {files.length > 0 && (
          <p className="text-xs text-accent-400 mt-2">
            {files.length}/{maxFiles} file{files.length !== 1 ? 's' : ''} selected
          </p>
        )}
      </div>

      {/* File previews */}
      {files.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {files.map((file, index) => {
            const previewUrl = URL.createObjectURL(file);
            const isImage = file.type.startsWith('image/');
            return (
              <div
                key={`${file.name}-${index}`}
                className="relative group rounded-lg overflow-hidden border border-slate-700 bg-slate-800"
              >
                {isImage ? (
                  <img
                    src={previewUrl}
                    alt={file.name}
                    className="w-full h-28 object-cover"
                    onLoad={() => URL.revokeObjectURL(previewUrl)}
                  />
                ) : (
                  <div className="w-full h-28 flex items-center justify-center bg-slate-700">
                    <ImageIcon size={28} className="text-slate-500" />
                  </div>
                )}
                <div className="p-1.5">
                  <p className="text-xs text-slate-400 truncate">{file.name}</p>
                  <p className="text-xs text-slate-600">{formatFileSize(file.size)}</p>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="absolute top-1 right-1 bg-slate-900/80 rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
                >
                  <X size={12} className="text-white" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {files.length > 1 && (
        <button
          onClick={() => onFilesChange([])}
          className="text-xs text-slate-500 hover:text-red-400 transition-colors"
        >
          Clear all files
        </button>
      )}
    </div>
  );
}
