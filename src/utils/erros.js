function primeiraMensagem(valor) {
  if (typeof valor === 'string') return valor
  if (Array.isArray(valor)) return valor.map(primeiraMensagem).find(Boolean) || ''
  if (valor && typeof valor === 'object') {
    return Object.values(valor).map(primeiraMensagem).find(Boolean) || ''
  }
  return ''
}

/** Mensagem legível de um erro do axios/DRF: detail, non_field_errors ou o primeiro erro de campo. */
export function mensagemErroApi(err, padrao = 'Não foi possível concluir a operação.') {
  const data = err?.response?.data
  if (!data) return padrao
  if (typeof data === 'string') return padrao
  return (
    primeiraMensagem(data.detail) ||
    primeiraMensagem(data.non_field_errors) ||
    primeiraMensagem(data) ||
    padrao
  )
}
