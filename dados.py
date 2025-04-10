import sqlite3
import json
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional

class GerenciadorTransacoes:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.inicializar()
        return cls._instance
    
    def inicializar(self):
        """Configura a conexão com o banco de dados e estrutura inicial"""
        self.backup_file = Path("dados_backup.json")
        self.con = sqlite3.connect("financas.db", check_same_thread=False)
        self.criar_estrutura()
        self.carregar_backup()
        
    def criar_estrutura(self):
        """Cria as tabelas necessárias se não existirem"""
        cursor = self.con.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                categoria TEXT NOT NULL,
                tipo TEXT NOT NULL,
                data DATE NOT NULL,
                removido_em DATETIME
            )
        """)
        self.con.commit()
        
    def carregar_backup(self):
        """Carrega dados de backup se existir"""
        if self.backup_file.exists():
            try:
                with open(self.backup_file, 'r') as f:
                    backup = json.load(f)
                
                cursor = self.con.cursor()
                cursor.executemany("""
                    INSERT OR IGNORE INTO transacoes 
                    (id, descricao, valor, categoria, tipo, data, removido_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, backup.get('transacoes', []))
                self.con.commit()
            except Exception as e:
                print(f"Erro ao carregar backup: {e}")
    
    def salvar_backup(self):
        """Salva um backup completo das transações"""
        transacoes = self.obter_todas_transacoes(include_removed=True)
        backup = {
            'data_backup': datetime.now().isoformat(),
            'transacoes': transacoes
        }
        
        try:
            with open(self.backup_file, 'w') as f:
                json.dump(backup, f, default=str)
        except Exception as e:
            print(f"Erro ao salvar backup: {e}")

    # Métodos CRUD
    def adicionar_transacao(self, transacao: Dict):
        """Adiciona uma nova transação"""
        cursor = self.con.cursor()
        cursor.execute("""
            INSERT INTO transacoes (descricao, valor, categoria, tipo, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            transacao['description'],
            transacao['amount'],
            transacao['category'],
            transacao['type'],
            transacao['date']
        ))
        self.con.commit()
    
    def obter_ultimas_transacoes(self, limite: int = 5) -> List[Dict]:
        """Obtém as últimas transações ativas"""
        cursor = self.con.cursor()
        cursor.execute("""
            SELECT id, descricao, valor, categoria, tipo, data
            FROM transacoes
            WHERE removido_em IS NULL
            ORDER BY data DESC
            LIMIT ?
        """, (limite,))
        return [dict(zip(['id', 'description', 'amount', 'category', 'type', 'date'], row)) 
                for row in cursor.fetchall()]
    
    def obter_transacoes_filtradas(self, 
                                 mes: Optional[int] = None, 
                                 ano: Optional[int] = None) -> List[Dict]:
        """Obtém transações com filtros de data"""
        query = """
            SELECT id, descricao, valor, categoria, tipo, data
            FROM transacoes
            WHERE removido_em IS NULL
        """
        params = []
        
        if ano:
            query += " AND strftime('%Y', data) = ?"
            params.append(str(ano))
        if mes:
            query += " AND strftime('%m', data) = ?"
            params.append(f"{mes:02d}")
        
        query += " ORDER BY data DESC"
        
        cursor = self.con.cursor()
        cursor.execute(query, params)
        return [dict(zip(['id', 'description', 'amount', 'category', 'type', 'date'], row)) 
                for row in cursor.fetchall()]
    
    def obter_total_por_tipo(self, 
                           tipo: str, 
                           mes: Optional[int] = None, 
                           ano: Optional[int] = None) -> float:
        """Calcula o total por tipo (income/expense)"""
        query = """
            SELECT COALESCE(SUM(valor), 0)
            FROM transacoes
            WHERE tipo = ? AND removido_em IS NULL
        """
        params = [tipo]
        
        if ano:
            query += " AND strftime('%Y', data) = ?"
            params.append(str(ano))
        if mes:
            query += " AND strftime('%m', data) = ?"
            params.append(f"{mes:02d}")
        
        cursor = self.con.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()[0]
    
    def remover_transacao(self, id: int):
        """Marca uma transação como removida (soft delete)"""
        cursor = self.con.cursor()
        cursor.execute("""
            UPDATE transacoes
            SET removido_em = ?
            WHERE id = ?
        """, (datetime.now(), id))
        self.con.commit()
    
    def obter_transacoes_removidas(self) -> List[Dict]:
        """Obtém todas as transações na lixeira"""
        cursor = self.con.cursor()
        cursor.execute("""
            SELECT id, descricao, valor, categoria, tipo, data, removido_em
            FROM transacoes
            WHERE removido_em IS NOT NULL
            ORDER BY removido_em DESC
        """)
        return [dict(zip(['id', 'description', 'amount', 'category', 'type', 'date', 'removed_at'], row)) 
                for row in cursor.fetchall()]
    
    def restaurar_transacao(self, id: int):
        """Restaura uma transação da lixeira"""
        cursor = self.con.cursor()
        cursor.execute("""
            UPDATE transacoes
            SET removido_em = NULL
            WHERE id = ?
        """, (id,))
        self.con.commit()
    
    def excluir_permanentemente(self, id: int):
        """Remove permanentemente uma transação"""
        cursor = self.con.cursor()
        cursor.execute("""
            DELETE FROM transacoes
            WHERE id = ?
        """, (id,))
        self.con.commit()
    
    def esvaziar_lixeira(self):
        """Remove permanentemente todas as transações na lixeira"""
        cursor = self.con.cursor()
        cursor.execute("""
            DELETE FROM transacoes
            WHERE removido_em IS NOT NULL
        """)
        self.con.commit()
    
    def obter_anos_disponiveis(self) -> List[int]:
        """Obtém todos os anos com transações"""
        cursor = self.con.cursor()
        cursor.execute("""
            SELECT DISTINCT strftime('%Y', data) as ano
            FROM transacoes
            WHERE removido_em IS NULL
            ORDER BY ano DESC
        """)
        return [int(row[0]) for row in cursor.fetchall() if row[0]]
    
    def obter_todas_transacoes(self, include_removed: bool = False) -> List[tuple]:
        """Obtém todas as transações para backup"""
        cursor = self.con.cursor()
        if include_removed:
            cursor.execute("SELECT * FROM transacoes")
        else:
            cursor.execute("SELECT * FROM transacoes WHERE removido_em IS NULL")
        return cursor.fetchall()