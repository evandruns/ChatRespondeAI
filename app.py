import streamlit as st
import os
import re
import urllib.parse
import random
import time
from typing import List, Set, Tuple
import pandas as pd
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import cloudscraper
import json
from datetime import datetime

# ---------------------------
# Configuração Inicial
# ---------------------------
st.set_page_config(
    page_title="Responde AI TOTVS",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# SISTEMA DE CACHE PARA MELHOR PERFORMANCE
# ---------------------------
class CacheManager:
    def __init__(self, ttl=3600):  # 1 hora de cache
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
    
    def clear(self):
        self.cache.clear()

cache = CacheManager()

# ---------------------------
# HEADERS MELHORADOS COM ROTAÇÃO DINÂMICA
# ---------------------------
def get_dynamic_headers(url=None):
    """Retorna headers dinâmicos e realistas"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
    ]
    
    base_headers = {
        'authority': 'centraldeatendimento.totvs.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'upgrade-insecure-requests': '1',
        'user-agent': random.choice(user_agents),
    }
    
    if url:
        base_headers['referer'] = 'https://centraldeatendimento.totvs.com/'
    
    return base_headers

# ---------------------------
# SISTEMA DE REQUISIÇÕES ROBUSTO
# ---------------------------
def create_advanced_scraper():
    """Cria um scraper avançado com retry automático"""
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            delay=10,
        )
        return scraper
    except Exception as e:
        st.warning(f"CloudScraper não disponível: {e}. Usando requests.")
        return requests.Session()

scraper = create_advanced_scraper()

def fazer_requisicao_inteligente(url, max_tentativas=3):
    """Sistema inteligente de requisições com múltiplas estratégias"""
    cache_key = f"req_{hash(url)}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    for tentativa in range(max_tentativas):
        try:
            # Delay progressivo entre tentativas
            if tentativa > 0:
                delay = tentativa * 2 + random.uniform(1, 3)
                time.sleep(delay)
            
            headers = get_dynamic_headers(url)
            
            # Tentar com CloudScraper primeiro
            response = scraper.get(url, headers=headers, timeout=25)
            
            if response.status_code == 200:
                # Verificar se não é uma página de bloqueio
                content_lower = response.text.lower()
                if not any(term in content_lower for term in ['access denied', 'blocked', 'bot detected', 'captcha']):
                    cache.set(cache_key, response)
                    return response
            
            # Se falhou, tentar com requests simples
            session = requests.Session()
            alt_headers = headers.copy()
            alt_headers['user-agent'] = random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
            ])
            
            response = session.get(url, headers=alt_headers, timeout=20)
            if response.status_code == 200:
                cache.set(cache_key, response)
                return response
                
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            continue
        except Exception as e:
            continue
    
    return None

# ---------------------------
# SISTEMA DE BUSCA APRIMORADO
# ---------------------------
def buscar_via_api_zendesk(query, max_results=5):
    """Busca usando a API oficial do Zendesk (método mais confiável)"""
    cache_key = f"api_search_{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        base_url = "https://centraldeatendimento.totvs.com/api/v2/help_center/pt-br/articles/search"
        params = {'query': query, 'per_page': max_results}
        
        headers = get_dynamic_headers()
        headers['accept'] = 'application/json'
        
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('results', [])
            
            links = []
            for article in articles:
                url = article.get('html_url')
                if url and url not in links:
                    links.append(url)
            
            cache.set(cache_key, links)
            return links
            
    except Exception as e:
        pass
    
    return []

def extrair_conteudo_via_api(url):
    """Extrai conteúdo via API - método mais confiável"""
    try:
        article_id = re.search(r'/articles/(\d+)', url)
        if not article_id:
            return None
            
        article_id = article_id.group(1)
        api_url = f"https://centraldeatendimento.totvs.com/api/v2/help_center/pt-br/articles/{article_id}"
        
        headers = get_dynamic_headers()
        headers['accept'] = 'application/json'
        
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            article = data.get('article', {})
            
            body = article.get('body', '')
            title = article.get('title', '')
            
            soup = BeautifulSoup(body, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            
            full_content = f"{title}\n\n{text}"
            return clean_text(full_content)[:6000]
            
    except Exception:
        pass
    
    return None

# ---------------------------
# STOP WORDS E PRÉ-PROCESSAMENTO (MELHORADO)
# ---------------------------
STOP_WORDS = {
    "bom dia", "boa tarde", "boa noite", "olá", "att", "atenciosamente",
    "cumprimentos", "obrigado", "obrigada", "prezado", "prezada",
    "caro", "cara", "senhor", "senhora", "ola", "oi", "saudações",
    "tudo bem", "tudo bem?", "amigo", "amiga", "por favor",
    "grato", "grata", "cordialmente", "abraço", "abs", "ok", "entendi",
    "obg", "vlw", "por favor", "favor", "gostaria", "queria", "saber"
}

PALAVRAS_TECNICAS = {
    'erp', 'sql', 'api', 'xml', 'json', 'tss', 'nt', 'danfe', 'nfe', 'cte',
    'mde', 'sped', 'ecd', 'ecf', 'efd', 'protheus', 'fluig', 'rm', 'log',
    'fis', 'fat', 'crm', 'com', 'tms', 'wms', 'bi', 'linx', 'datasul'
}

def clean_query(query: str) -> str:
    """Limpa e otimiza a query para busca"""
    if not query:
        return ""
    
    # Remover caracteres especiais mas manter acentos
    query = re.sub(r'[^\w\sáàâãéèêíïóôõöúçñÁÀÂãÉÈÊÍÏÓÔÕÖÚÇÑ-]', ' ', query)
    query = query.lower().strip()
    
    # Remover stop words mas manter palavras técnicas
    parts = query.split()
    keep = []
    
    for p in parts:
        p_clean = p.strip()
        if (p_clean not in STOP_WORDS and len(p_clean) >= 2) or p_clean in PALAVRAS_TECNICAS:
            keep.append(p_clean)
    
    # Adicionar "Protheus" se não estiver presente e for uma consulta técnica
    if keep and "protheus" not in " ".join(keep).lower():
        termos_tecnicos = any(term in " ".join(keep).lower() for term in 
                            ['configurar', 'parâmetro', 'erro', 'funcionalidade', 'módulo'])
        if termos_tecnicos:
            keep.append("protheus")
    
    return " ".join(keep)

def clean_text(text: str) -> str:
    """Limpa texto extraído com algoritmos melhorados"""
    if not text or pd.isna(text):
        return ""
    
    # Remover caracteres nulos e problemas de encoding
    text = text.replace("\0", " ").replace("\r", " ").replace("\t", " ")
    
    # Remover padrões comuns de lixo
    patterns = [
        r'Anexo\(s\):.*',
        r'Compartilhar:.*',
        r'Comentários.*',
        r'Artigo criado.*Artigo atualizado.*',
        r'©\s*\d{4}.*TOTVS',
        r'https?://\S+',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remover HTML tags
    text = re.sub(r'<[^>]*>', ' ', text)
    
    # Normalizar espaços
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def tem_video_ou_anexo(query: str) -> bool:
    """Verifica se a query se refere a conteúdo multimídia"""
    padroes = [
        r"\banexo\b", r"\banexos\b", r"\banexado\b", r"\banexada\b",
        r"\bv[íi]deo\b", r"\bv[íi]deos\b", r"\bgravaç[ãa]o\b",
        r"\bprint\b", r"\bimagem\b", r"\bscreenshot\b", r"\bfoto\b",
        r"\bpdf\b", r"\barquivo\b", r"\bdownload\b"
    ]
    query_lower = query.lower()
    return any(re.search(p, query_lower) for p in padroes)

# ---------------------------
# SISTEMA DE EXTRAÇÃO MELHORADO
# ---------------------------
def extrair_conteudo_pagina(url: str) -> str:
    """Extrai conteúdo com múltiplas estratégias"""
    if '/search?' in url:
        return "Página de pesquisa - conteúdo não extraído"

    # Tentar via API primeiro (método mais confiável)
    conteudo_api = extrair_conteudo_via_api(url)
    if conteudo_api:
        return conteudo_api

    # Fallback para scraping tradicional
    try:
        response = fazer_requisicao_inteligente(url)
        
        if not response:
            return f"❌ Não foi possível acessar: {url}"
            
        if response.status_code != 200:
            return f"Erro HTTP {response.status_code}: {url}"

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remover elementos desnecessários
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe']):
            element.decompose()
        
        # Estratégias de seleção melhoradas
        content_selectors = [
            "article",
            ".article-body",
            ".article-content", 
            "main",
            ".content",
            ".post-content",
            "[role='main']",
            ".help-center-content"
        ]
        
        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break
        
        # Limpar elementos específicos
        if content:
            cleanup_selectors = [
                '.article-meta', '.article-info', '.article-votes',
                '.comments', '.share-buttons', '.breadcrumb',
                '.related-articles', '.article-attachments'
            ]
            
            for selector in cleanup_selectors:
                for element in content.select(selector):
                    element.decompose()
            
            text = content.get_text(separator=' ', strip=True)
        else:
            # Fallback estratégico
            body = soup.find('body')
            text = body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)
        
        cleaned_text = clean_text(text)
        return cleaned_text[:6000] if cleaned_text else "Conteúdo não encontrado"
        
    except Exception as e:
        return f"Erro na extração: {str(e)}"

def pesquisar_interna_totvs(query: str, limit: int = 5) -> List[str]:
    """Pesquisa interna com fallbacks"""
    cache_key = f"internal_search_{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    base = "https://centraldeatendimento.totvs.com"
    search_url = f"{base}/hc/pt-br/search?query={urllib.parse.quote(query)}"
    
    links = []
    try:
        response = fazer_requisicao_inteligente(search_url)
        
        if response and response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Múltiplos seletores para robustez
            selectors = [
                "a[href*='/articles/']",
                ".search-result a",
                ".article-list a",
                ".article-link"
            ]
            
            for selector in selectors:
                for a in soup.select(selector):
                    href = a.get("href", "")
                    if href:
                        if href.startswith("/"):
                            href = base + href
                        elif not href.startswith("http"):
                            href = base + "/" + href.lstrip("/")
                            
                        if href.startswith(base) and "/articles/" in href and href not in links:
                            links.append(href)
                            
                    if len(links) >= limit:
                        break
                if len(links) >= limit:
                    break
                    
    except Exception as e:
        pass
    
    cache.set(cache_key, links)
    return links

def buscar_documentacao_totvs(query: str, max_links: int = 5) -> List[str]:
    """Sistema híbrido de busca com múltiplas fontes"""
    cache_key = f"search_{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    cleaned = clean_query(query)
    if not cleaned:
        return []
    
    found = []
    seen = set()
    
    # Estratégia 1: API Zendesk (mais confiável)
    api_links = buscar_via_api_zendesk(cleaned, max_links)
    for url in api_links:
        if url not in seen:
            found.append(url)
            seen.add(url)
    
    # Estratégia 2: DuckDuckGo
    if len(found) < max_links:
        try:
            search_query = f"site:centraldeatendimento.totvs.com {cleaned}"
            with DDGS() as ddgs:
                for r in ddgs.text(search_query, max_results=10):
                    url = r.get("href", "")
                    if (url.startswith("https://centraldeatendimento.totvs.com") and 
                        "/articles/" in url and url not in seen):
                        found.append(url)
                        seen.add(url)
                    if len(found) >= max_links:
                        break
        except Exception as e:
            pass
    
    # Estratégia 3: Pesquisa interna
    if len(found) < max_links:
        interna_links = pesquisar_interna_totvs(cleaned, max_links - len(found))
        for url in interna_links:
            if url not in seen:
                found.append(url)
                seen.add(url)
    
    # Fallback final
    if not found:
        found = [f"https://centraldeatendimento.totvs.com/hc/pt-br/search?query={urllib.parse.quote(cleaned)}"]
    
    cache.set(cache_key, found)
    return found[:max_links]

# ---------------------------
# SISTEMA DE RELEVÂNCIA MELHORADO
# ---------------------------
def pontuar_relevancia(texto: str, query: str) -> float:
    """Sistema de pontuação de relevância melhorado"""
    if not texto or not query:
        return 0.0
    
    tokens_query = set(clean_query(query).split())
    tokens_texto = set(texto.lower().split())
    
    if not tokens_query or not tokens_texto:
        return 0.0
    
    # Pontuação baseada na interseção
    intersection = tokens_query & tokens_texto
    base_score = len(intersection) / len(tokens_query)
    
    # Bônus para correspondências exatas
    exact_matches = sum(1 for token in tokens_query if token in texto.lower())
    exact_bonus = exact_matches * 0.1
    
    # Bônus para palavras técnicas
    tech_bonus = sum(0.05 for token in intersection if token in PALAVRAS_TECNICAS)
    
    final_score = min(base_score + exact_bonus + tech_bonus, 1.0)
    return final_score

# ---------------------------
# SISTEMA IA MELHORADO COM TRATAMENTO DE ERROS
# ---------------------------
def reclassificar_artigos_ia(artigos: List[Tuple[float, str, str]], query: str, use_gemini: bool, api_key: str, modelo: str) -> List[Tuple[float, str, str]]:
    """Usa IA para reclassificar os artigos por relevância"""
    if not artigos or len(artigos) <= 1:
        return artigos
    
    cache_key = f"reclass_{hash(query + ''.join(url for _, url, _ in artigos))}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        artigos_info = []
        for score, url, conteudo in artigos:
            titulo = url.split('/')[-1].replace('-', ' ')[:100]
            preview = conteudo[:200] + "..." if conteudo and len(conteudo) > 50 else "Conteúdo não disponível"
            artigos_info.append(f"URL: {url}\nTítulo: {titulo}\nConteúdo: {preview}\n---")
        
        artigos_texto = "\n".join(artigos_info)
        
        if use_gemini:
            resposta = reclassificar_gemini(query, artigos_texto, modelo, api_key)
        else:
            resposta = reclassificar_openai(query, artigos_texto, modelo, api_key)
        
        artigos_ordenados = processar_resposta_reclassificacao(resposta, artigos)
        
        if artigos_ordenados:
            cache.set(cache_key, artigos_ordenados)
            return artigos_ordenados
        else:
            resultado = sorted(artigos, reverse=True, key=lambda x: x[0])
            cache.set(cache_key, resultado)
            return resultado
            
    except Exception as e:
        st.error(f"Erro na reclassificação por IA: {e}")
        resultado = sorted(artigos, reverse=True, key=lambda x: x[0])
        cache.set(cache_key, resultado)
        return resultado

def reclassificar_gemini(query: str, artigos_texto: str, model: str, api_key: str) -> str:
    """Reclassifica artigos usando Gemini com tratamento robusto de erros"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Configuração de segurança para evitar respostas bloqueadas
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH", 
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
        
        prompt = f"""
        Analise estes artigos da documentação TOTVS e ordene-os por relevância para a pergunta do usuário.
        
        PERGUNTA DO USUÁRIO: {query}
        
        ARTIGOS ENCONTRADOS:
        {artigos_texto}
        
        INSTRUÇÕES:
        1. Analise cada artigo em relação à pergunta
        2. Ordene do MAIS RELEVANTE para o MENOS RELEVANTE  
        3. Retorne APENAS os URLs em ordem de relevância, um por linha
        4. Não inclua explicações, apenas a lista ordenada de URLs
        5. Se não puder determinar a relevância, retorne os URLs na ordem original
        
        URLs ORDENADOS:
        """
        
        # Usar modelo mais estável
        if model not in ["gemini-2.5-flash", "gemini-2.5-pro"]:
            model = "gemini-2.5-flash"
            
        gemini_model = genai.GenerativeModel(
            model_name=model,
            safety_settings=safety_settings,
            generation_config={
                "temperature": 0.0,
                "max_output_tokens": 500,
            }
        )
        
        response = gemini_model.generate_content([prompt])
        
        # Tratamento robusto da resposta
        if response and response.parts:
            return response.text.strip()
        elif response and response.candidates:
            # Tentar extrair texto dos candidatos
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    return candidate.content.parts[0].text.strip()
        
        return ""  # Retorna string vazia em caso de erro
        
    except Exception as e:
        st.warning(f"Aviso Gemini: {e}")
        return ""  # Retorna string vazia em caso de erro

def reclassificar_openai(query: str, artigos_texto: str, model: str, api_key: str) -> str:
    """Reclassifica artigos usando OpenAI"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Analise estes artigos da documentação TOTVS e ordene-os por relevância para a pergunta do usuário.
        
        PERGUNTA DO USUÁRIO: {query}
        
        ARTIGOS ENCONTRADOS:
        {artigos_texto}
        
        INSTRUÇÕES:
        1. Analise cada artigo em relação à pergunta
        2. Ordene do MAIS RELEVANTE para o MENOS RELEVANTE
        3. Retorne APENAS os URLs em ordem de relevância, um por linha
        4. Não inclua explicações, apenas a lista ordenada de URLs
        """
        
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um especialista em classificar documentação técnica por relevância."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"Erro OpenAI: {e}")

def processar_resposta_reclassificacao(resposta_ia: str, artigos_originais: List[Tuple[float, str, str]]) -> List[Tuple[float, str, str]]:
    """Processa a resposta da IA e reordena os artigos"""
    if not resposta_ia:
        return []
    
    # Extrair URLs da resposta
    urls_ordenados = []
    for linha in resposta_ia.split('\n'):
        linha = linha.strip()
        if linha.startswith('http'):
            urls_ordenados.append(linha)
    
    # Criar mapa de artigos por URL
    artigo_por_url = {url: (score, url, conteudo) for score, url, conteudo in artigos_originais}
    
    # Reordenar baseado na classificação da IA
    artigos_ordenados = []
    for url in urls_ordenados:
        if url in artigo_por_url:
            artigos_ordenados.append(artigo_por_url[url])
    
    # Adicionar quaisquer artigos que não foram classificados pela IA
    urls_adicionados = set(urls_ordenados)
    for artigo in artigos_originais:
        if artigo[1] not in urls_adicionados:
            artigos_ordenados.append(artigo)
    
    return artigos_ordenados

def formatar_links_saiba_mais(links: List[str]) -> str:
    """Formata os links para a seção Saiba Mais"""
    if not links:
        return ""
    
    padroes_de_remocao = ["-Cross", "-CROSS", "-RH", "-MP", "-Logística", "-Framework", "-LOG", "-FIN", "-FAT", "-CRM"]
    
    links_formatados = []
    for link in links:
        link_limpo = link
        for padrao in padroes_de_remocao:
            posicao = link.find(padrao)
            if posicao != -1:
                link_limpo = link[:posicao]
                break
        links_formatados.append(link_limpo)
    
    # Remover duplicatas mantendo a ordem
    links_unicos = []
    for link in links_formatados:
        if link not in links_unicos:
            links_unicos.append(link)
    
    # Formatar a seção Saiba Mais
    saiba_mais = "\n\n**🔗 Saiba mais:**\n"
    for i, link in enumerate(links_unicos[:5], 1):  # Limitar a 5 links
        saiba_mais += f"{i}. {link}\n"
    
    return saiba_mais

def get_ai_response(query: str, context: str, fontes: List[str], modelo: str, use_gemini: bool, api_key: str, temperatura: float):
    """Função unificada que escolhe entre Gemini e ChatGPT com tratamento robusto"""
    
    # Filtrar contexto removendo mensagens de erro
    if "erro 403" in context.lower() or "acesso negado" in context.lower():
        context = "Conteúdo não disponível devido a restrições de acesso."
    
    if not context or not context.strip() or context == "Conteúdo não disponível devido a restrições de acesso.":
        return "Não encontrei essa informação na documentação oficial devido a restrições de acesso."

    try:
        if use_gemini:
            return get_gemini_response_robusto(query, context, fontes, modelo, api_key, temperatura)
        else:
            return get_chatgpt_response(query, context, fontes, modelo, api_key, temperatura)
    except Exception as e:
        return f"Erro ao processar a resposta: {str(e)}"

def get_gemini_response_robusto(query: str, context: str, fontes: List[str], model: str, api_key: str, temperatura: float):
    """Versão robusta do Gemini com tratamento completo de erros"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Configurações de segurança relaxadas
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
        
        generation_config = {
            "temperature": min(temperatura, 0.7),  # Limitar temperatura para evitar problemas
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        # Usar modelo mais estável
        if model not in ["gemini-2.5-flash", "gemini-2.5-pro"]:
            model = "gemini-2.5-flash"
        
        gemini_model = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        system_prompt = (
            "Você é um analista de suporte especializado no ERP Protheus da TOTVS.\n"
            "Responda de forma técnica, precisa e baseada exclusivamente no contexto fornecido.\n"
            "- Se a informação não estiver no contexto, responda apenas: \"Não encontrei essa informação na documentação oficial\".\n"
            "- Seja objetivo e inclua passos acionáveis quando aplicável.\n"
            "- NÃO inclua a seção 'Fontes consultadas' no final - isso será adicionado automaticamente.\n"
        )

        user_content = (
            f"{system_prompt}\n\n"
            f"PERGUNTA DO USUÁRIO:\n{query}\n\n"
            f"CONTEÚDO EXTRAÍDO:\n{context}\n\n"
            "Fontes disponíveis:\n" + "\n".join(fontes)
        )

        response = gemini_model.generate_content([user_content])
        
        # Tratamento robusto da resposta
        if response and response.parts:
            return response.text.strip()
        elif response and response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    return candidate.content.parts[0].text.strip()
        
        # Fallback se a resposta estiver vazia
        return "Não foi possível gerar uma resposta para esta consulta."
        
    except Exception as e:
        return f"Erro ao processar a solicitação: {str(e)}"

def get_chatgpt_response(query: str, context: str, fontes: List[str], model: str, api_key: str, temperatura: float):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        system_prompt = (
            "Você é um analista de suporte especializado no ERP Protheus da TOTVS.\n"
            "Responda de forma técnica, precisa e baseada exclusivamente no contexto fornecido.\n"
            "- Se a informação não estiver no contexto, responda apenas: \"Não encontrei essa informação na documentação oficial\".\n"
            "- Seja objetivo e inclua passos acionáveis quando aplicável.\n"
            "- NÃO inclua a seção 'Fontes consultadas' no final - isso será adicionado automaticamente.\n"
        )
        
        user_content = f"PERGUNTA DO USUÁRIO:\n{query}\n\nCONTEÚDO EXTRAÍDO:\n{context}\n\nFontes disponíveis:\n" + "\n".join(fontes)

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperatura,
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro ao gerar resposta com OpenAI: {e}"

# ---------------------------
# INTERFACE STREAMLIT MELHORADA
# ---------------------------
def inicializar_session_state():
    """Inicializa as variáveis de session state"""
    defaults = {
        'min_score': 0.3,
        'use_gemini': True,
        'modelo': "gemini-2.5-flash", 
        'api_key': "",
        'temperatura': 0.1,
        'mostrar_codigo': False,
        'reclassificar_ia': True,
        'cache_enabled': True,
        'historico': []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def atualizar_lista_modelos():
    """Atualiza a lista de modelos baseado na escolha Gemini/OpenAI"""
    if st.session_state.use_gemini:
        modelos_disponiveis = ["gemini-2.5-flash", "gemini-2.5-pro"]
        if st.session_state.modelo not in modelos_disponiveis:
            st.session_state.modelo = "gemini-2.5-flash"
    else:
        modelos_disponiveis = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        if not any(model in st.session_state.modelo for model in ["gpt", "openai"]):
            st.session_state.modelo = "gpt-4o-mini"
    return modelos_disponiveis

def adicionar_ao_historico(pergunta, resposta):
    """Adiciona interação ao histórico"""
    if 'historico' not in st.session_state:
        st.session_state.historico = []
    
    st.session_state.historico.append({
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'pergunta': pergunta,
        'resposta': resposta[:500] + "..." if len(resposta) > 500 else resposta
    })
    
    # Manter apenas os últimos 10 itens
    if len(st.session_state.historico) > 10:
        st.session_state.historico = st.session_state.historico[-10:]

def processar_pergunta(user_query: str):
    """Processa a pergunta do usuário e retorna a resposta"""
    # Verificar se a API key foi configurada
    if not st.session_state.api_key:
        return "Erro: Chave da API não configurada. Por favor, configure sua chave na sidebar."
    
    cleaned_query = clean_query(user_query)
    if not cleaned_query:
        return "Não foi possível processar a pergunta."

    if tem_video_ou_anexo(user_query):
        return "Pergunta contém referência a vídeo ou anexo. Não será feita busca automática na documentação."
    
    try:
        # Buscar links
        with st.status("Buscando na documentação TOTVS...", expanded=True) as status:
            status.write("🔍 Procurando artigos relevantes...")
            links = buscar_documentacao_totvs(user_query, max_links=5)
            
            if not links:
                return "Não foram encontrados artigos relevantes na documentação TOTVS."
            
            status.write(f"📚 Encontrados {len(links)} artigos. Extraindo conteúdo...")
            contexto_scores = []
            
            # Extrair conteúdo dos links
            for i, link in enumerate(links):
                status.write(f"📖 Lendo artigo {i+1}/{len(links)}...")
                texto = extrair_conteudo_pagina(link)
                score = pontuar_relevancia(texto, user_query)
                contexto_scores.append((score, link, texto))

            # Reclassificação inteligente por IA
            if st.session_state.reclassificar_ia and len(contexto_scores) > 1:
                status.write("🧠 Reclassificando artigos por relevância...")
                contexto_scores = reclassificar_artigos_ia(
                    contexto_scores, 
                    user_query, 
                    st.session_state.use_gemini,
                    st.session_state.api_key,
                    st.session_state.modelo
                )
            else:
                # Ordenação tradicional por score
                contexto_scores.sort(reverse=True, key=lambda x: x[0])
            
            status.write("🤖 Gerando resposta com IA...")
            
            # Usar os 3 artigos mais relevantes para o contexto
            artigos_relevantes = contexto_scores[:3]
            contexto_combinado = "\n\n".join([conteudo for _, _, conteudo in artigos_relevantes if conteudo.strip()])
            
            # Gerar resposta
            if not contexto_combinado.strip():
                resposta_final = "Atenção: não foi possível validar essa informação específica na documentação oficial."
            elif contexto_scores[0][0] < st.session_state.min_score:
                resposta_final = "Observação: essa consulta aborda um ponto não detalhado na documentação. A resposta é baseada em conhecimento geral.\n\n"
                resposta_final += get_ai_response(
                    user_query, 
                    contexto_combinado, 
                    [link for _, link, _ in artigos_relevantes], 
                    st.session_state.modelo,
                    st.session_state.use_gemini,
                    st.session_state.api_key,
                    st.session_state.temperatura
                )
            else:
                resposta_final = get_ai_response(
                    user_query, 
                    contexto_combinado, 
                    [link for _, link, _ in artigos_relevantes], 
                    st.session_state.modelo,
                    st.session_state.use_gemini,
                    st.session_state.api_key,
                    st.session_state.temperatura
                )
            
            # Adicionar seção "Saiba mais" se a resposta for válida
            mensagens_erro = [
                "não foi possível validar essa informação específica",
                "não encontrei essa informação na documentação oficial",
                "conteúdo não disponível devido a restrições de acesso",
                "erro ao processar",
                "não foi possível gerar"
            ]
            
            resposta_valida = not any(erro in resposta_final.lower() for erro in mensagens_erro)
            
            if resposta_valida and links:
                saiba_mais = formatar_links_saiba_mais([link for _, link, _ in contexto_scores[:5]])
                resposta_final += saiba_mais
            
            status.update(label="Processamento completo!", state="complete")
            
        # Adicionar ao histórico
        adicionar_ao_historico(user_query, resposta_final)
        return resposta_final

    except Exception as e:
        return f"Ocorreu um erro durante o processamento: {str(e)}"

def main():
    # Inicializar session state
    inicializar_session_state()
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações Avançadas")
        
        # Configurações básicas
        st.session_state.use_gemini = st.checkbox(
            "Usar Google Gemini", 
            value=st.session_state.use_gemini,
            help="Desmarque para usar OpenAI"
        )
        
        modelos_disponiveis = atualizar_lista_modelos()
        
        # Configurações de performance
        st.subheader("🚀 Performance")
        
        st.session_state.cache_enabled = st.checkbox(
            "Ativar Cache", 
            value=st.session_state.cache_enabled,
            help="Melhora performance armazenando resultados temporariamente"
        )
        
        if st.button("🧹 Limpar Cache"):
            cache.clear()
            st.success("Cache limpo!")
        
        st.session_state.reclassificar_ia = st.checkbox(
            "Reclassificação por IA", 
            value=st.session_state.reclassificar_ia,
            help="Usa IA para ordenar resultados por relevância"
        )
        
        st.session_state.min_score = st.slider(
            "Score Mínimo de Relevância",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.min_score,
            step=0.05,
            help="Valores mais baixos retornam mais resultados"
        )
        
        st.session_state.temperatura = st.slider(
            "Temperatura da IA",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperatura,
            step=0.1,
            help="0 = preciso, 1 = criativo"
        )
        
        # Modelo e API
        st.session_state.modelo = st.selectbox(
            "Modelo de IA",
            options=modelos_disponiveis,
            index=modelos_disponiveis.index(st.session_state.modelo)
        )
        
        st.session_state.api_key = st.text_input(
            "Chave da API",
            value=st.session_state.api_key,
            type="password",
            placeholder="Cole sua chave da API aqui"
        )
        
        # Histórico
        if st.session_state.get('historico'):
            st.subheader("📚 Histórico")
            for i, item in enumerate(reversed(st.session_state.historico[-5:])):
                with st.expander(f"{item['timestamp']} - {item['pergunta'][:50]}..."):
                    st.write(f"**P:** {item['pergunta']}")
                    st.write(f"**R:** {item['resposta']}")
        
        st.markdown("---")
        st.info("""
        **💡 Dicas:**
        - Use termos técnicos específicos
        - Score 0.2-0.4 para mais resultados
        - Ative o cache para melhor performance
        - Temperatura 0.1-0.3 para respostas precisas
        """)
        
        st.markdown("---")
        st.caption("By Evandro Narciso Santos")
    
    # Conteúdo principal
    st.title("🤖 Responde AI TOTVS")
    st.markdown("Sua assistente inteligente para dúvidas sobre o **ERP Protheus**")
    
    # Indicador de configuração
    ai_provider = "Google Gemini" if st.session_state.use_gemini else "OpenAI"
    temp_desc = "Preciso" if st.session_state.temperatura <= 0.3 else "Balanceado" if st.session_state.temperatura <= 0.7 else "Criativo"
    reclass_desc = "✅ Ativa" if st.session_state.reclassificar_ia else "❌ Inativa"
    cache_desc = "✅ Ativo" if st.session_state.cache_enabled else "❌ Inativo"
    
    st.caption(f"🔧 Configurado: {ai_provider} | Modelo: {st.session_state.modelo} | Score: {st.session_state.min_score} | Temperatura: {st.session_state.temperatura} ({temp_desc}) | Reclassificação IA: {reclass_desc} | Cache: {cache_desc}")
    
    # Área de entrada da pergunta
    user_query = st.text_area(
        "**Digite sua pergunta:**",
        placeholder="Ex: Como configurar parâmetros financeiros no Protheus?",
        height=150,
        help="Descreva sua dúvida técnica sobre o ERP Protheus"
    )
    
    # Botão de envio
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚀 Enviar Pergunta", type="primary", use_container_width=True):
            if not user_query.strip():
                st.warning("Por favor, digite sua pergunta.")
            else:
                if not st.session_state.api_key:
                    st.error("❌ Configure sua chave da API na sidebar para continuar.")
                else:
                    resposta = processar_pergunta(user_query)
                    st.session_state.resposta = resposta
                    st.session_state.mostrar_codigo = False
    
    with col2:
        if st.button("🧹 Limpar", use_container_width=True):
            if 'resposta' in st.session_state:
                del st.session_state.resposta
            st.session_state.mostrar_codigo = False
            st.rerun()
    
    # Exibir resposta se existir
    if 'resposta' in st.session_state and st.session_state.resposta:
        st.markdown("---")
        st.subheader("📋 Resposta:")
        
        # Controles para a resposta
        col_controls1, col_controls2, col_controls3 = st.columns([2, 1, 1])
        
        with col_controls1:
            # Toggle entre visualização normal e código
            if st.button("📄 Visualizar como Código" if not st.session_state.mostrar_codigo else "📝 Visualizar Normal", 
                        key="toggle_view", use_container_width=True):
                st.session_state.mostrar_codigo = not st.session_state.mostrar_codigo
                st.rerun()
        
        with col_controls2:
            # Botão para copiar (usando st.code que tem cópia nativa)
            if st.button("📋 Copiar Resposta", key="copy_btn", use_container_width=True):
                # Mostrar a resposta em formato código que permite cópia fácil
                st.session_state.mostrar_codigo = True
                st.success("✅ Use Ctrl+C para copiar o texto acima!")
        
        with col_controls3:
            # Botão para baixar
            if st.button("💾 Baixar", key="download_btn", use_container_width=True):
                st.download_button(
                    label="📥 Clique para baixar",
                    data=st.session_state.resposta,
                    file_name=f"resposta_totvs_{time.strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    key="download_file"
                )
        
        # Exibir a resposta
        if st.session_state.mostrar_codigo:
            # Modo código - fácil de copiar
            st.code(st.session_state.resposta, language="text", line_numbers=False)
            st.info("💡 **Dica:** Selecione o texto acima e use Ctrl+C para copiar")
        else:
            # Modo normal - melhor visualização
            st.write(st.session_state.resposta)

if __name__ == "__main__":
    main()
