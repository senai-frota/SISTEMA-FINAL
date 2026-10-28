import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  errosParaFormulario,
  interpretarErroApi,
  mensagemErroApi,
  textoCampo,
} from './erros.js'

test('textoCampo aceita string, lista e objeto aninhado', () => {
  assert.equal(textoCampo({ matricula: ['Já cadastrada.'] }, 'matricula'), 'Já cadastrada.')
  assert.equal(textoCampo({ matricula: 'Já cadastrada.' }, 'matricula'), 'Já cadastrada.')
  assert.equal(textoCampo({ email: { 0: 'Informe um e-mail válido.' } }, 'email'), 'Informe um e-mail válido.')
  assert.equal(textoCampo({}, 'nome'), '')
})

test('erro de campo unique não é tratado como falha de conexão', () => {
  const err = { response: { status: 400, data: { matricula: ['Esta matrícula já está cadastrada.'] } } }
  const info = interpretarErroApi(err)
  assert.equal(info.rede, false)
  assert.equal(info.campos.matricula, 'Esta matrícula já está cadastrada.')
  assert.equal(info.geral, '')
  assert.equal(mensagemErroApi(err), 'Esta matrícula já está cadastrada.')
})

test('detail vira mensagem geral', () => {
  const err = { response: { status: 403, data: { detail: 'Apenas administradores podem criar usuários.' } } }
  const info = interpretarErroApi(err)
  assert.equal(info.geral, 'Apenas administradores podem criar usuários.')
  assert.equal(info.autorizacao, true)
})

test('HTML ou string em 413 não inventa causa de validação', () => {
  const err = { response: { status: 413, data: '<html>entity too large</html>' } }
  assert.equal(mensagemErroApi(err), 'O arquivo é maior do que o permitido.')
})

test('falha de rede não parece validação', () => {
  const err = { message: 'Network Error', code: 'ERR_NETWORK' }
  const info = interpretarErroApi(err, 'Falha')
  assert.equal(info.rede, true)
  assert.match(info.geral, /conectar ao servidor/)
})

test('500 não expõe detalhe interno ao usuário', () => {
  const err = { response: { status: 500, data: { detail: 'Internal Server Error' } } }
  assert.match(mensagemErroApi(err), /Tente novamente mais tarde/)
})

test('503 preserva mensagem operacional da API', () => {
  const err = {
    response: {
      status: 503,
      data: { detail: 'Consulta FIPE indisponível no momento. Cadastre o veículo manualmente.' },
    },
  }
  assert.match(mensagemErroApi(err), /FIPE/)
})

test('errosParaFormulario preenche campos e non_field_errors', () => {
  const form = errosParaFormulario({
    response: { status: 400, data: { email: ['Informe um e-mail válido.'], detail: 'Corrija os campos.' } },
  })
  assert.deepEqual(form.email, ['Informe um e-mail válido.'])
  assert.deepEqual(form.non_field_errors, ['Corrija os campos.'])
})

test('401 orienta a autenticar de novo quando não há detalhe', () => {
  const err = { response: { status: 401, data: {} } }
  assert.match(mensagemErroApi(err), /sessão expirou/)
})

test('timeout de rede não é apresentado como validação', () => {
  const info = interpretarErroApi({ code: 'ECONNABORTED', message: 'timeout of 120000ms exceeded' })
  assert.equal(info.rede, true)
  assert.match(info.geral, /conectar ao servidor/)
})

test('429 informa excesso de tentativas', () => {
  assert.match(
    mensagemErroApi({ response: { status: 429, data: {} } }),
    /Muitas tentativas/,
  )
})

test('erro só de campo não vira também mensagem geral', () => {
  const form = errosParaFormulario({
    response: { status: 400, data: { matricula: ['Esta matrícula já está cadastrada.'] } },
  })
  assert.deepEqual(form.matricula, ['Esta matrícula já está cadastrada.'])
  assert.equal(form.non_field_errors, undefined)
})

test('404 e 403 distinguem ausência e autorização', () => {
  assert.match(mensagemErroApi({ response: { status: 404, data: {} } }), /não foi encontrado/)
  const info = interpretarErroApi({ response: { status: 403, data: {} } })
  assert.equal(info.autorizacao, true)
  assert.match(info.geral, /não tem permissão/)
})
