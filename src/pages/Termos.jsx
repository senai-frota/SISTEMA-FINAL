import { useAuth } from '../context/AuthContext'
import TermosAdmin from './TermosAdmin'
import MeuTermo from './MeuTermo'

export default function Termos() {
  const { isAdmin } = useAuth()
  return isAdmin ? <TermosAdmin /> : <MeuTermo />
}
