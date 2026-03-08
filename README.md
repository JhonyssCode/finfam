# 💚 FinFam — Controle Financeiro Familiar

App web em Python/Flask para controle financeiro familiar com dados pessoais e compartilhados. Valores em **R$ (Real brasileiro)**.

## Funcionalidades
- 🔐 Autenticação multi-usuário com convites familiares
- ↔️ Transações pessoais e familiares com categorias, filtros e exportação CSV
- ✎ Edição e exclusão de transações
- 🎯 Orçamento mensal por categoria com alertas e cópia do mês anterior
- 📋 Contas a pagar/receber com recorrência mensal e alertas de vencimento
- 📊 Dashboard com gráficos entradas vs saídas + alertas inteligentes
- 📈 Relatórios avançados: filtro por período/âmbito/membro, taxa de poupança, maiores despesas, exportação CSV
- 🏷️ Gestão de categorias com ícone e cor personalizáveis

## Instalação

```bash
# 1. Entrar na pasta do projeto
cd finfam

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env e altere SECRET_KEY para algo seguro

# 5. Iniciar o servidor
python run.py
```

## Acesso
Abra o browser em: **http://localhost:5000**

Na primeira vez, crie uma conta — o primeiro usuário é automaticamente o **Admin** da família e pode convidar outros membros em **Menu → Convidar**.

## Rede local (celular, outros computadores)
O servidor já roda em `0.0.0.0:5000`. Descubra o IP do computador:
- Linux/Mac: `ip addr` ou `ifconfig`
- Windows: `ipconfig`

Acesse de outros dispositivos: `http://192.168.x.x:5000`

## Stack
- **Backend:** Python 3.10+ / Flask 3
- **Banco de dados:** SQLite (arquivo local `instance/finfam.db`)
- **Frontend:** Jinja2 + Chart.js (sem build step necessário)
- **Autenticação:** Flask-Login
