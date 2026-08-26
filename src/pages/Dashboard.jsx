import { useAuth } from '../context/AuthContext'
import AdminDashboard from './AdminDashboard'
import UserDashboard from './UserDashboard'

export default function Dashboard() {
  const { isAdmin } = useAuth()

  return isAdmin ? <AdminDashboard /> : <UserDashboard />
}