"""
Export Service
Generates export reports in multiple formats: JSON, CSV, HTML
"""

import json
import csv
from typing import List, Dict, Any
from io import StringIO
from datetime import datetime
from database import Database


class ExportService:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
    
    def export_json(self) -> str:
        """Export all data as JSON with structure matching requirements."""
        stats = self.db.get_stats()
        duplicates = self.db.get_duplicates()
        largest = self.db.get_largest_files(100) # Top 100
        oldest = self.db.get_oldest_files(100)   # Top 100
        
        data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_files": stats["total_files"],
                "total_size_bytes": stats["total_size"],
                "formatted_size": self._format_bytes(stats["total_size"])
            },
            "file_type_distribution": stats["extensions"],
            "duplicates": {
                "total_groups": len(duplicates),
                "total_wasted_space": sum(d['wasted_space'] for d in duplicates),
                "groups": duplicates
            },
            "largest_files": largest,
            "oldest_files": oldest
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def export_csv(self) -> str:
        """Export comprehensive report as multi-section CSV."""
        output = StringIO()
        writer = csv.writer(output)
        
        stats = self.db.get_stats()
        duplicates = self.db.get_duplicates()
        largest = self.db.get_largest_files(100)
        oldest = self.db.get_oldest_files(100)
        
        # --- SECTION 1: SUMARIO ---
        writer.writerow(['--- SUMÁRIO ---'])
        writer.writerow(['Data do Relatório', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Total de Arquivos', stats['total_files']])
        writer.writerow(['Tamanho Total', self._format_bytes(stats['total_size'])])
        writer.writerow([])
        
        # --- SECTION 2: DISTRIBUIÇÃO POR TIPO ---
        writer.writerow(['--- DISTRIBUIÇÃO POR TIPO ---'])
        writer.writerow(['Extensão', 'Quantidade', 'Tamanho Total', 'Percentual'])
        total_size = stats['total_size'] or 1
        for ext in stats['extensions']:
            percent = (ext['total_size'] / total_size) * 100
            writer.writerow([
                ext['extension'] or '(sem extensão)',
                ext['count'],
                self._format_bytes(ext['total_size']),
                f"{percent:.2f}%"
            ])
        writer.writerow([])
        
        # --- SECTION 3: TOP 10 MAIORES ARQUIVOS ---
        writer.writerow(['--- TOP 100 MAIORES ARQUIVOS ---'])
        writer.writerow(['Caminho', 'Nome', 'Tamanho', 'Modificado em'])
        for f in largest:
            writer.writerow([
                f['path'],
                f['filename'],
                self._format_bytes(f['size_bytes']),
                datetime.fromtimestamp(f['modified_at']).strftime('%Y-%m-%d %H:%M:%S') if f['modified_at'] else ''
            ])
        writer.writerow([])
        
        # --- SECTION 4: ARQUIVOS MAIS ANTIGOS ---
        writer.writerow(['--- TOP 100 ARQUIVOS MAIS ANTIGOS ---'])
        writer.writerow(['Caminho', 'Nome', 'Tamanho', 'Criado em', 'Modificado em'])
        for f in oldest:
            writer.writerow([
                f['path'],
                f['filename'],
                self._format_bytes(f['size_bytes']),
                datetime.fromtimestamp(f['created_at']).strftime('%Y-%m-%d %H:%M:%S') if f['created_at'] else '',
                datetime.fromtimestamp(f['modified_at']).strftime('%Y-%m-%d %H:%M:%S') if f['modified_at'] else ''
            ])
        writer.writerow([])

        # --- SECTION 5: DUPLICADOS ---
        writer.writerow(['--- ARQUIVOS DUPLICADOS ---'])
        writer.writerow(['Grupo Hash (MD5)', 'Quantidade', 'Espaço Desperdiçado', 'Caminhos'])
        for d in duplicates:
            paths = " | ".join(d['paths'])
            writer.writerow([
                d['md5_hash'],
                d['count'],
                self._format_bytes(d['wasted_space']),
                paths
            ])
            
        return output.getvalue()
    
    def _format_bytes(self, bytes_val):
        """Helper to format bytes."""
        if not bytes_val: return '0 B'
        k = 1024
        sizes = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while bytes_val >= k and i < len(sizes) - 1:
            bytes_val /= k
            i += 1
        return f"{bytes_val:.2f} {sizes[i]}"

    def export_html(self) -> str:
        """Export comprehensive report as self-contained HTML."""
        stats = self.db.get_stats()
        duplicates = self.db.get_duplicates()
        largest = self.db.get_largest_files(100)
        oldest = self.db.get_oldest_files(100)
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório do Catalogador Inteligente - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 3rem 2rem;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            font-size: 1.125rem;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 2rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}
        
        .stat-card {{
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            border-left: 4px solid #667eea;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 0.5rem;
        }}
        
        .stat-label {{
            color: #6c757d;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .section {{
            margin-bottom: 3rem;
        }}
        
        .section h2 {{
            font-size: 1.75rem;
            margin-bottom: 1.5rem;
            color: #2d3748;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.5rem;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 0.875rem 1rem;
            border-bottom: 1px solid #e9ecef;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .duplicate-group {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 8px;
        }}
        
        .duplicate-header {{
            font-weight: 600;
            color: #856404;
            margin-bottom: 0.5rem;
        }}
        
        .file-path {{
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
            color: #495057;
            padding: 0.25rem 0;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 2rem;
            text-align: center;
            color: #6c757d;
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 Relatório do Catalogador Inteligente</h1>
            <p>Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        </div>
        
        <div class="content">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{stats['total_files']:,}</div>
                    <div class="stat-label">Total de Arquivos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{self._format_bytes(stats['total_size'])}</div>
                    <div class="stat-label">Tamanho Total</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(duplicates)}</div>
                    <div class="stat-label">Grupos Duplicados</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{sum(d['count'] for d in duplicates)}</div>
                    <div class="stat-label">Arquivos Duplicados</div>
                </div>
            </div>
            
            <div class="section">
                <h2>📊 Top 10 Extensões por Tamanho</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Extensão</th>
                            <th>Quantidade</th>
                            <th>Tamanho Total</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        # Extensions table
        for ext in stats['extensions'][:10]:
            html += f"""
                        <tr>
                            <td><strong>{ext['extension'] or 'Sem extensão'}</strong></td>
                            <td>{ext['count']:,}</td>
                            <td>{self._format_bytes(ext['total_size'])}</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>📦 100 Maiores Arquivos</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Arquivo</th>
                            <th>Tamanho</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        # Largest files table
        for idx, file in enumerate(largest[:100], 1):
            html += f"""
                        <tr>
                            <td>{idx}</td>
                            <td class="file-path">{file['path']}</td>
                            <td><strong>{self._format_bytes(file['size_bytes'])}</strong></td>
                        </tr>"""
                        
        html += """
                    </tbody>
                </table>
            </div>"""
        
        # Duplicates section
        if duplicates:
            html += """
            <div class="section">
                <h2>📋 Arquivos Duplicados</h2>"""
            
            for dup in duplicates[:50]:  # Limit to top 50
                html += f"""
                <div class="duplicate-group">
                    <div class="duplicate-header">
                        MD5: {dup['md5_hash']} • {dup['count']} cópias • 
                        Desperdiçado: {self._format_bytes(dup['wasted_space'])}
                    </div>"""
                
                for path in dup['paths']:
                    html += f'<div class="file-path">{path}</div>'
                
                html += """
                </div>"""
            
            html += """
            </div>"""
        
        html += f"""
        </div>
        
        <div class="footer">
            <strong>Catalogador Inteligente de Arquivos</strong><br>
            Este relatório foi gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
        
        return html
