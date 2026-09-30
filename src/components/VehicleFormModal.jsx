import { useEffect, useState } from 'react'
import api from '../services/api'
import Modal from './Modal'

const COMBUSTIVEIS = [
  { value: 'flex', label: 'Flex' },
  { value: 'gasolina', label: 'Gasolina' },
  { value: 'etanol', label: 'Etanol' },
  { value: 'diesel', label: 'Diesel' },
  { value: 'eletrico', label: 'Elétrico' },
  { value: 'hibrido', label: 'Híbrido' },
]

const STATUS = [
  { value: 'disponivel', label: 'Disponível' },
  { value: 'em_uso', label: 'Em uso' },
  { value: 'manutencao', label: 'Em manutenção' },
  { value: 'inativo', label: 'Inativo' },
]

const empty = {
  placa: '',
  modelo: '',
  marca: '',
  ano: new Date().getFullYear(),
  cor: '',
  tipo_combustivel: 'flex',
  capacidade: 5,
  status: 'disponivel',
  observacoes: '',
  km_atual: 0,
  data_ultima_manutencao: '',
}

/*
 * ============================================================
 * PLACA
 * ============================================================
 */

function validarPlaca(placa) {
  const placaLimpa = placa
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')

  const placaAntiga = /^[A-Z]{3}[0-9]{4}$/
  const placaMercosul = /^[A-Z]{3}[0-9][A-Z][0-9]{2}$/

  return (
    placaAntiga.test(placaLimpa) ||
    placaMercosul.test(placaLimpa)
  )
}

function normalizarPlaca(placa) {
  return placa
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
}

/*
 * ============================================================
 * COMBUSTÍVEL
 * ============================================================
 */

function detectarCombustivel(nome) {
  const texto = nome.toLowerCase()

  if (texto.includes('flex')) {
    return 'flex'
  }

  if (texto.includes('gasolina')) {
    return 'gasolina'
  }

  if (texto.includes('etanol')) {
    return 'etanol'
  }

  if (texto.includes('diesel')) {
    return 'diesel'
  }

  if (
    texto.includes('elétrico') ||
    texto.includes('eletrico')
  ) {
    return 'eletrico'
  }

  if (
    texto.includes('híbrido') ||
    texto.includes('hibrido')
  ) {
    return 'hibrido'
  }

  return 'flex'
}

/*
 * ============================================================
 * SIMPLIFICAR MODELO
 * ============================================================
 *
 * Exemplos:
 *
 * Astra 2.0 8V/ CD 2.0 8V Hatchbak 5p Aut
 * -> Astra
 *
 * Corolla XEi 2.0 Flex
 * -> Corolla
 *
 * Onix 1.0 Turbo Flex
 * -> Onix
 *
 * HB20 Comfort Plus 1.0
 * -> HB20
 */

function simplificarModelo(nome) {
  if (!nome) {
    return ''
  }

  let texto = nome
    .trim()
    .replace(/\s+/g, ' ')

  /*
   * Remove informações que normalmente são
   * especificações técnicas do motor.
   *
   * Exemplos:
   * 1.0
   * 1.4
   * 1.6
   * 2.0
   * 8V
   * 16V
   * Turbo
   * Flex
   * Gasolina
   * Diesel
   */

  texto = texto
    .replace(/\b\d+\.\d+\b/g, '')
    .replace(/\b\d+V\b/gi, '')
    .replace(/\bTurbo\b/gi, '')
    .replace(/\bFlex\b/gi, '')
    .replace(/\bGasolina\b/gi, '')
    .replace(/\bEtanol\b/gi, '')
    .replace(/\bDiesel\b/gi, '')
    .replace(/\bElétrico\b/gi, '')
    .replace(/\bEletrico\b/gi, '')
    .replace(/\bHíbrido\b/gi, '')
    .replace(/\bHibrido\b/gi, '')

  /*
   * Remove especificações de carroceria,
   * transmissão e quantidade de portas.
   */

  texto = texto
    .replace(/\bHatchback\b/gi, '')
    .replace(/\bHatchbak\b/gi, '')
    .replace(/\bSedan\b/gi, '')
    .replace(/\bSedã\b/gi, '')
    .replace(/\bSUV\b/gi, '')
    .replace(/\bPick[- ]?up\b/gi, '')
    .replace(/\bWagon\b/gi, '')
    .replace(/\bCabine Dupla\b/gi, '')
    .replace(/\bCabine Simples\b/gi, '')
    .replace(/\bAutomático\b/gi, '')
    .replace(/\bAutomatica\b/gi, '')
    .replace(/\bAutomática\b/gi, '')
    .replace(/\bManual\b/gi, '')
    .replace(/\bAut\b/gi, '')
    .replace(/\bMec\b/gi, '')
    .replace(/\b\d+p\b/gi, '')

  /*
   * Remove códigos técnicos que aparecem
   * depois de uma barra.
   *
   * Exemplo:
   *
   * Astra 2.0 8V/ CD 2.0 8V
   *
   * O conteúdo depois da "/" geralmente
   * é especificação da versão.
   */

  texto = texto.split('/')[0]

  /*
   * Limpa caracteres sobrando.
   */

  texto = texto
    .replace(/\s+/g, ' ')
    .replace(/\s*[-/]\s*$/g, '')
    .trim()

  /*
   * Se depois da limpeza não sobrou nada,
   * utiliza o primeiro termo original.
   */

  if (!texto) {
    return nome.trim().split(' ')[0]
  }

  /*
   * Algumas palavras são apenas especificações
   * e não devem aparecer sozinhas como modelo.
   */

  const palavras = texto.split(' ')

  const resultado = []

  for (const palavra of palavras) {
    if (!palavra) {
      continue
    }

    resultado.push(palavra)
  }

  return resultado.join(' ')
}

/*
 * ============================================================
 * COMPONENTE
 * ============================================================
 */

export default function VehicleFormModal({
  veiculo,
  onClose,
  onSaved,
}) {
  const [form, setForm] = useState(() => {
    if (!veiculo) return empty
    return {
      ...empty,
      placa: veiculo.placa || '',
      marca: veiculo.marca || '',
      modelo: veiculo.modelo || '',
      ano: veiculo.ano || new Date().getFullYear(),
      cor: veiculo.cor || '',
      tipo_combustivel: veiculo.tipo_combustivel || 'flex',
      capacidade: veiculo.capacidade ?? 5,
      status: veiculo.status || 'disponivel',
      observacoes: veiculo.observacoes || '',
      km_atual: veiculo.km_atual ?? 0,
      data_ultima_manutencao: veiculo.data_ultima_manutencao
        ? String(veiculo.data_ultima_manutencao).slice(0, 10)
        : '',
    }
  })

  const isEdit = !!veiculo

  const [marcas, setMarcas] = useState([])
  const [modelos, setModelos] = useState([])
  const [anos, setAnos] = useState([])

  const [codigoMarca, setCodigoMarca] = useState('')
  const [codigoModelo, setCodigoModelo] = useState('')

  const [loadingMarcas, setLoadingMarcas] = useState(true)
  const [loadingModelos, setLoadingModelos] = useState(false)
  const [loadingAnos, setLoadingAnos] = useState(false)

  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  /*
   * ============================================================
   * CARREGAR MARCAS
   * ============================================================
   */

  useEffect(() => {
    async function carregarMarcas() {
      setLoadingMarcas(true)

      try {
        const { data } = await api.get(
          '/veiculos/marcas/'
        )

        setMarcas(data)
      } catch (err) {
        console.error(
          'Erro ao carregar marcas:',
          err
        )

        setErrors({
          marcas:
            'Não foi possível carregar as marcas.',
        })
      } finally {
        setLoadingMarcas(false)
      }
    }

    carregarMarcas()
  }, [])

  /*
   * ============================================================
   * QUANDO A MARCA MUDA
   * ============================================================
   */

  useEffect(() => {
    if (!codigoMarca) {
      setModelos([])
      setAnos([])
      setCodigoModelo('')

      return
    }

    async function carregarModelos() {
      setLoadingModelos(true)

      setModelos([])
      setAnos([])
      setCodigoModelo('')

      try {
        const { data } = await api.get(
          `/veiculos/marcas/${codigoMarca}/modelos/`
        )

        setModelos(data.modelos || [])
      } catch (err) {
        console.error(
          'Erro ao carregar modelos:',
          err
        )

        setErrors({
          modelos:
            'Não foi possível carregar os modelos.',
        })
      } finally {
        setLoadingModelos(false)
      }
    }

    carregarModelos()
  }, [codigoMarca])

  /*
   * ============================================================
   * QUANDO O MODELO MUDA
   * ============================================================
   */

  useEffect(() => {
    if (!codigoMarca || !codigoModelo) {
      setAnos([])
      return
    }

    async function carregarAnos() {
      setLoadingAnos(true)
      setAnos([])

      try {
        const { data } = await api.get(
          `/veiculos/marcas/${codigoMarca}/modelos/${codigoModelo}/anos/`
        )

        setAnos(data)
      } catch (err) {
        console.error(
          'Erro ao carregar anos:',
          err
        )

        setErrors({
          anos:
            'Não foi possível carregar os anos.',
        })
      } finally {
        setLoadingAnos(false)
      }
    }

    carregarAnos()
  }, [codigoMarca, codigoModelo])

  /*
   * ============================================================
   * ATUALIZAR CAMPO
   * ============================================================
   */

  function update(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
  }

  /*
   * ============================================================
   * MARCA
   * ============================================================
   */

  function handleMarcaChange(e) {
    const codigo = e.target.value

    setCodigoMarca(codigo)

    const marcaSelecionada = marcas.find(
      (marca) =>
        String(marca.codigo) === String(codigo)
    )

    update(
      'marca',
      marcaSelecionada?.nome || ''
    )

    update('modelo', '')
    update('ano', '')

    setCodigoModelo('')
  }

  /*
   * ============================================================
   * MODELO
   * ============================================================
   */

  function handleModeloChange(e) {
    const codigo = e.target.value

    setCodigoModelo(codigo)

    const modeloSelecionado = modelos.find(
      (modelo) =>
        String(modelo.codigo) === String(codigo)
    )

    const nomeSimplificado = simplificarModelo(
      modeloSelecionado?.nome || ''
    )

    update(
      'modelo',
      nomeSimplificado
    )

    update('ano', '')
  }

  /*
   * ============================================================
   * ANO
   * ============================================================
   */

  function handleAnoChange(e) {
    const codigo = e.target.value

    const anoSelecionado = anos.find(
      (ano) =>
        String(ano.codigo) === String(codigo)
    )

    if (!anoSelecionado) {
      update('ano', '')
      return
    }

    const ano = parseInt(
      anoSelecionado.nome.split(' ')[0],
      10
    )

    const combustivel =
      detectarCombustivel(
        anoSelecionado.nome
      )

    update('ano', ano)
    update(
      'tipo_combustivel',
      combustivel
    )
  }

  /*
   * ============================================================
   * PLACA
   * ============================================================
   */

  function handlePlacaChange(e) {
    const valor = e.target.value
      .toUpperCase()
      .replace(/[^A-Z0-9-]/g, '')

    if (valor.length > 8) {
      return
    }

    update('placa', valor)

    if (errors.placa) {
      setErrors((current) => ({
        ...current,
        placa: undefined,
      }))
    }
  }

  /*
   * ============================================================
   * ENVIO
   * ============================================================
   */

  async function handleSubmit(e) {
    e.preventDefault()

    setErrors({})

    if (!validarPlaca(form.placa)) {
      setErrors({
        placa: [
          'Informe uma placa válida. Use ABC-1234 ou ABC1D23.',
        ],
      })

      return
    }

    if (!form.marca) {
      setErrors({
        marca: ['Selecione uma marca.'],
      })

      return
    }

    if (!form.modelo) {
      setErrors({
        modelo: ['Selecione um modelo.'],
      })

      return
    }

    if (!form.ano) {
      setErrors({
        ano: ['Selecione um ano.'],
      })

      return
    }

    setSaving(true)

    try {
      const dados = {
        placa: normalizarPlaca(form.placa),
        marca: form.marca,
        modelo: isEdit ? form.modelo : simplificarModelo(form.modelo),
        ano: Number(form.ano),
        cor: form.cor,
        tipo_combustivel: form.tipo_combustivel,
        capacidade: Number(form.capacidade),
        status: form.status,
        observacoes: form.observacoes || '',
        km_atual: Number(form.km_atual || 0),
        data_ultima_manutencao: form.data_ultima_manutencao || null,
      }

      if (veiculo) {
        await api.patch(
          `/veiculos/${veiculo.id}/`,
          dados
        )
      } else {
        await api.post(
          '/veiculos/',
          dados
        )
      }

      onSaved()
    } catch (err) {
      console.error(
        'Erro ao salvar veículo:',
        err
      )

      if (
        err.response?.data &&
        typeof err.response.data ===
          'object'
      ) {
        setErrors(
          err.response.data
        )
      } else {
        setErrors({
          non_field_errors: [
            'Não foi possível salvar. Tente novamente.',
          ],
        })
      }
    } finally {
      setSaving(false)
    }
  }

  /*
   * ============================================================
   * RENDER
   * ============================================================
   */

  return (
    <Modal
      title={
        veiculo
          ? 'Editar veículo'
          : 'Novo veículo'
      }
      onClose={onClose}
      width={560}
    >
      <form
        onSubmit={handleSubmit}
        className="form-grid"
      >
        {/* PLACA + STATUS */}

        <div className="field-row">
          <label className="field">
            <span>Placa</span>

            <input
              value={form.placa}
              onChange={handlePlacaChange}
              placeholder="ABC-1234 ou ABC1D23"
              maxLength={8}
              required
              autoComplete="off"
            />

            {errors.placa && (
              <small className="field-error">
                {Array.isArray(errors.placa) ? errors.placa[0] : errors.placa}
              </small>
            )}
          </label>

          <label className="field">
            <span>Status</span>

            <select
              value={form.status}
              onChange={(e) => update('status', e.target.value)}
            >
              {STATUS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {/* MARCA + MODELO */}

        <div className="field-row">
          <label className="field">
            <span>Marca</span>

            {isEdit ? (
              <input
                value={form.marca}
                onChange={(e) => update('marca', e.target.value)}
                required
              />
            ) : (
              <select
                value={codigoMarca}
                onChange={handleMarcaChange}
                disabled={loadingMarcas}
                required
              >
                <option value="">
                  {loadingMarcas
                    ? 'Carregando marcas…'
                    : 'Selecione uma marca'}
                </option>

                {marcas.map((marca) => (
                  <option key={marca.codigo} value={marca.codigo}>
                    {marca.nome}
                  </option>
                ))}
              </select>
            )}

            {errors.marca && (
              <small className="field-error">
                {Array.isArray(errors.marca) ? errors.marca[0] : errors.marca}
              </small>
            )}
          </label>

          <label className="field">
            <span>Modelo</span>

            {isEdit ? (
              <input
                value={form.modelo}
                onChange={(e) => update('modelo', e.target.value)}
                required
              />
            ) : (
              <select
                value={codigoModelo}
                onChange={handleModeloChange}
                disabled={!codigoMarca || loadingModelos}
                required
              >
                <option value="">
                  {!codigoMarca
                    ? 'Selecione uma marca primeiro'
                    : loadingModelos
                      ? 'Carregando modelos…'
                      : 'Selecione um modelo'}
                </option>

                {modelos.map((modelo) => (
                  <option key={modelo.codigo} value={modelo.codigo}>
                    {simplificarModelo(modelo.nome)}
                  </option>
                ))}
              </select>
            )}

            {errors.modelo && (
              <small className="field-error">
                {Array.isArray(errors.modelo) ? errors.modelo[0] : errors.modelo}
              </small>
            )}
          </label>
        </div>

        {/* ANO */}

        <div className="field-row">
          <label className="field">
            <span>Ano</span>

            {isEdit ? (
              <input
                type="number"
                min={1990}
                max={new Date().getFullYear() + 1}
                value={form.ano}
                onChange={(e) => update('ano', e.target.value)}
                required
              />
            ) : (
              <select
                value={
                  anos.find((ano) => {
                    const anoNumerico = parseInt(ano.nome.split(' ')[0], 10)
                    return anoNumerico === Number(form.ano)
                  })?.codigo || ''
                }
                onChange={handleAnoChange}
                disabled={!codigoModelo || loadingAnos}
                required
              >
                <option value="">
                  {!codigoModelo
                    ? 'Selecione um modelo primeiro'
                    : loadingAnos
                      ? 'Carregando anos…'
                      : 'Selecione um ano'}
                </option>

                {anos.map((ano) => (
                  <option key={ano.codigo} value={ano.codigo}>
                    {ano.nome}
                  </option>
                ))}
              </select>
            )}

            {errors.ano && (
              <small className="field-error">
                {Array.isArray(errors.ano) ? errors.ano[0] : errors.ano}
              </small>
            )}
          </label>

          {/* COR */}

          <label className="field">
            <span>Cor</span>

            <input
              value={form.cor}
              onChange={(e) =>
                update(
                  'cor',
                  e.target.value
                )
              }
              required
            />
          </label>
        </div>

        {/* COMBUSTÍVEL + CAPACIDADE */}

        <div className="field-row">
          <label className="field">
            <span>
              Combustível
            </span>

            <select
              value={
                form.tipo_combustivel
              }
              onChange={(e) =>
                update(
                  'tipo_combustivel',
                  e.target.value
                )
              }
            >
              {COMBUSTIVEIS.map(
                (c) => (
                  <option
                    key={c.value}
                    value={c.value}
                  >
                    {c.label}
                  </option>
                )
              )}
            </select>
          </label>

          <label className="field">
            <span>Lugares</span>

            <input
              type="number"
              min={1}
              value={
                form.capacidade
              }
              onChange={(e) =>
                update(
                  'capacidade',
                  e.target.value
                )
              }
              required
            />
          </label>
        </div>

        <div className="field-row">
          <label className="field">
            <span>KM atual</span>
            <input
              type="number"
              min={0}
              step="1"
              value={form.km_atual ?? 0}
              onChange={(e) => update('km_atual', e.target.value)}
              required
            />
            {errors.km_atual && (
              <small className="field-error">
                {Array.isArray(errors.km_atual) ? errors.km_atual[0] : errors.km_atual}
              </small>
            )}
          </label>
          <label className="field">
            <span>Última manutenção</span>
            <input
              type="date"
              value={form.data_ultima_manutencao || ''}
              onChange={(e) => update('data_ultima_manutencao', e.target.value)}
            />
          </label>
        </div>

        {/* OBSERVAÇÕES */}

        <label className="field">
          <span>
            Observações
          </span>

          <textarea
            rows={2}
            value={
              form.observacoes || ''
            }
            onChange={(e) =>
              update(
                'observacoes',
                e.target.value
              )
            }
          />
        </label>

        {errors.non_field_errors && (
          <div className="form-error">
            {Array.isArray(
              errors.non_field_errors
            )
              ? errors
                  .non_field_errors[0]
              : errors.non_field_errors}
          </div>
        )}

        <div className="modal-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onClose}
            disabled={saving}
          >
            Cancelar
          </button>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving
              ? 'Salvando…'
              : 'Salvar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}