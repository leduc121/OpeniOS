import { useState } from 'react'

export default function App() {
  const [count, setCount] = useState(0)
  const [text, setText] = useState('')

  return (
    <div style={{ textAlign: 'center', padding: '10px 0' }}>
      <div style={{
        display: 'inline-block',
        padding: '4px 12px',
        borderRadius: '12px',
        backgroundColor: 'rgba(52, 199, 89, 0.2)',
        color: '#34c759',
        fontSize: '12px',
        fontWeight: '600',
        marginBottom: '16px'
      }}>
        Vite HMR Active
      </div>

      <h1 id="app-title" style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '8px', color: '#ff9f0a' }}>
        🔥 OpeniOS Live HMR Verified 🔥
      </h1>

      <p id="app-version" style={{ fontSize: '14px', color: '#30d158', fontWeight: 'bold', marginBottom: '24px' }}>
        Version: 4.0.0 (VERIFIED HMR LIVE ON HYPRLAND)
      </p>

      <div style={{
        backgroundColor: '#1c1c1e',
        borderRadius: '16px',
        padding: '20px',
        marginBottom: '20px',
        border: '1px solid #2c2c2e'
      }}>
        <div style={{ fontSize: '14px', color: '#a1a1a6', marginBottom: '12px' }}>
          Interactive React State
        </div>
        <div id="react-counter" style={{ fontSize: '32px', fontWeight: 'bold', color: '#0a84ff', marginBottom: '16px' }}>
          {count}
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
          <button
            id="btn-decrement"
            onClick={() => setCount(c => c - 1)}
            style={{
              padding: '10px 20px',
              borderRadius: '10px',
              backgroundColor: '#2c2c2e',
              color: '#fff',
              border: 'none',
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            -
          </button>
          <button
            id="btn-increment"
            onClick={() => setCount(c => c + 1)}
            style={{
              padding: '10px 20px',
              borderRadius: '10px',
              backgroundColor: '#0a84ff',
              color: '#fff',
              border: 'none',
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            +
          </button>
        </div>
      </div>

      <div style={{
        backgroundColor: '#1c1c1e',
        borderRadius: '16px',
        padding: '16px',
        border: '1px solid #2c2c2e'
      }}>
        <input
          id="react-input"
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Test React input binding..."
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: '#000',
            border: '1px solid #3a3a3c',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '14px',
            outline: 'none'
          }}
        />
        {text && (
          <div id="react-input-mirror" style={{ marginTop: '10px', fontSize: '13px', color: '#30d158' }}>
            Bound: {text}
          </div>
        )}
      </div>
    </div>
  )
}
