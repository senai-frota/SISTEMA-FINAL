const CAMPOS_GERAIS = new Set(['detail', 'non_field_errors', 'message', 'error'])

function primeiraMensagem(valor) {
  if (valor == null || valor === '') return ''
  if (typeof valor === 'string') return valor.trim()
  if (Array.isArray(valor)) return valor.map(primeiraMensagem).find(Boolean) || ''
  if (typeof valor === 'object') {
    return Object.values(valor).map(primeiraMensagem).find(Boolean) || ''
  }
  return String(valor)
}

/** Texto de um campo de erro DRF (string, lista ou objeto). */
export function textoCampo(errors, nome) {
  if (!errors || typeof errors !== 'object') return ''
  return primeiraMensagem(errors[nome])
}

function mensagemPorStatus(status, padrao) {
  if (status === 401) return 'Sua sessão expirou. Entre novamente.'
  if (status === 403) return 'Você não tem permissão para esta operação.'
  if (status === 404) return 'O registro não foi encontrado.'
  if (status === 409) return 'Esta operação conflita com um registro existente.'
  if (status === 413) return 'O arquivo é maior do que o permitido.'
  if (status === 422) return 'Os dados enviados não puderam ser processados.'
  if (status === 429) return 'Muitas tentativas. Aguarde um momento e tente novamente.'
  if (status === 502 || status === 503 || status === 504) {
    return 'O serviço está temporariamente indisponível. Tente novamente mais tarde.'
  }
  if (status >= 500) return 'Não foi possível concluir a operação. Tente novamente mais tarde.'
  return padrao
}

function camposDePayload(data) {
  const campos = {}
  if (!data || typeof data !== 'object' || Array.isArray(data)) return campos
  Object.entries(data).forEach(([chave, valor]) => {
    if (CAMPOS_GERAIS.has(chave)) return
    const texto = primeiraMensagem(valor)
    if (texto) campos[chave] = texto
  })
  return campos
}

/**
 * Interpreta um erro Axios/DRF.
 * `campos` tem mensagens por nome de campo; `geral` é o aviso fora dos campos.
 */
export function interpretarErroApi(err, padrao = 'Não foi possível concluir a operação.') {
  const status = err?.response?.status
  const data = err?.response?.data
  const codigo = err?.code

  if (!err?.response) {
    const rede =
      codigo === 'ECONNABORTED' ||
      codigo === 'ERR_NETWORK' ||
      err?.message === 'Network Error'
    return {
      status: null,
      campos: {},
      geral: rede
        ? 'Não foi possível conectar ao servidor. Verifique a conexão e tente novamente.'
        : padrao,
      rede: true,
      autenticacao: false,
      autorizacao: false,
    }
  }

  const campos = typeof data === 'object' && data && !Array.isArray(data)
    ? camposDePayload(data)
    : {}
  const geralPayload =
    primeiraMensagem(data?.detail) ||
    primeiraMensagem(data?.non_field_errors) ||
    primeiraMensagem(data?.message) ||
    (typeof data === 'string' ? '' : '') ||
    (Array.isArray(data) ? primeiraMensagem(data) : '')

  const porStatus = mensagemPorStatus(status, padrao)
  let geral = geralPayload
  if (status >= 500 && status !== 503) {
    geral = porStatus
  } else if (!geral) {
    geral = Object.keys(campos).length ? '' : porStatus
  }

  return {
    status,
    campos,
    geral,
    rede: false,
    autenticacao: status === 401,
    autorizacao: status === 403,
  }
}

/** Mensagem única para toast ou alerta (campo ou geral). */
export function mensagemErroApi(err, padrao = 'Não foi possível concluir a operação.') {
  const info = interpretarErroApi(err, padrao)
  if (info.geral) return info.geral
  const primeiroCampo = Object.values(info.campos)[0]
  return primeiroCampo || padrao
}

/** Formato usado pelos formulários (listas por campo + non_field_errors). */
export function errosParaFormulario(err, padrao = 'Não foi possível concluir a operação.') {
  const info = interpretarErroApi(err, padrao)
  const saida = {}
  Object.entries(info.campos).forEach(([chave, texto]) => {
    saida[chave] = [texto]
  })
  if (info.geral) saida.non_field_errors = [info.geral]
  return saida
}
