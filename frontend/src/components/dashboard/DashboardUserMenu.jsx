import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Globe, LogOut, ImagePlus, Trash2 } from 'lucide-react'
import {
  clearProfileAvatar,
  getProfileAvatar,
  MAX_AVATAR_BYTES,
  storeProfileAvatar,
} from '../../api/auth'
import { getInitials } from '../../utils/auth'

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('Could not read image file'))
    reader.readAsDataURL(file)
  })
}

export default function DashboardUserMenu({ user, onLogout }) {
  const navigate = useNavigate()
  const email = user?.email ?? ''
  const initials = user?.initials || getInitials(email)

  const [avatarUrl, setAvatarUrl] = useState(() => getProfileAvatar(email))
  const [menuOpen, setMenuOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [uploadError, setUploadError] = useState(null)

  const rootRef = useRef(null)
  const fileRef = useRef(null)

  useEffect(() => {
    setAvatarUrl(getProfileAvatar(email))
  }, [email])

  useEffect(() => {
    function handleClickOutside(e) {
      if (!rootRef.current?.contains(e.target)) {
        setMenuOpen(false)
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function closeAll() {
    setMenuOpen(false)
    setNotifOpen(false)
  }

  async function handlePhotoChange(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    setUploadError(null)
    if (!file.type.startsWith('image/')) {
      setUploadError('Please choose an image file.')
      return
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setUploadError('Image must be 500KB or smaller.')
      return
    }

    try {
      const dataUrl = await readFileAsDataUrl(file)
      storeProfileAvatar(email, dataUrl)
      setAvatarUrl(dataUrl)
    } catch {
      setUploadError('Could not upload image. Try again.')
    }
  }

  function handleRemovePhoto() {
    clearProfileAvatar(email)
    setAvatarUrl(null)
    setUploadError(null)
  }

  return (
    <div className="admin-topbar-r" ref={rootRef}>
      <div className="admin-topbar-action">
        <button
          type="button"
          className="admin-icon-btn"
          aria-label="Notifications"
          aria-expanded={notifOpen}
          onClick={() => {
            setNotifOpen((open) => !open)
            setMenuOpen(false)
          }}
        >
          <Bell size={20} />
        </button>
        {notifOpen && (
          <div className="admin-dropdown admin-dropdown-notif" role="dialog" aria-label="Notifications">
            <div className="admin-dropdown-title">Notifications</div>
            <p className="admin-dropdown-empty">No notifications yet</p>
          </div>
        )}
      </div>

      <div className="admin-topbar-action">
        <button
          type="button"
          className="admin-avatar admin-avatar-btn"
          title={email}
          aria-label="Account menu"
          aria-expanded={menuOpen}
          onClick={() => {
            setMenuOpen((open) => !open)
            setNotifOpen(false)
          }}
        >
          {avatarUrl ? (
            <img src={avatarUrl} alt="" className="admin-avatar-img" />
          ) : (
            initials
          )}
        </button>

        {menuOpen && (
          <div className="admin-dropdown admin-user-menu" role="menu">
            <div className="admin-user-menu-head">
              <div className="admin-user-menu-name">{user?.name || 'Cooperative Admin'}</div>
              <div className="admin-user-menu-email">{email}</div>
            </div>

            {uploadError && (
              <div className="admin-user-menu-error">{uploadError}</div>
            )}

            <button
              type="button"
              className="admin-user-menu-item"
              role="menuitem"
              onClick={() => fileRef.current?.click()}
            >
              <ImagePlus size={16} /> Change profile photo
            </button>

            {avatarUrl && (
              <button
                type="button"
                className="admin-user-menu-item"
                role="menuitem"
                onClick={handleRemovePhoto}
              >
                <Trash2 size={16} /> Remove photo
              </button>
            )}

            <button
              type="button"
              className="admin-user-menu-item"
              role="menuitem"
              onClick={() => {
                closeAll()
                navigate('/')
              }}
            >
              <Globe size={16} /> Back to main website
            </button>

            <div className="admin-user-menu-divider" />

            <button
              type="button"
              className="admin-user-menu-item admin-user-menu-item-danger"
              role="menuitem"
              onClick={() => {
                closeAll()
                onLogout?.()
              }}
            >
              <LogOut size={16} /> Log out
            </button>
          </div>
        )}
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        hidden
        onChange={handlePhotoChange}
      />
    </div>
  )
}
