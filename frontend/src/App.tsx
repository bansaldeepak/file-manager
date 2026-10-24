import './styles/tokens.css';
import './styles/reset.css';
import { AppShell } from './components/AppShell';

function App() {
  return (
    <AppShell
      toolbar={
        <span style={{ fontFamily: 'var(--font-body)', fontSize: '13px', fontWeight: 500, color: 'var(--color-text-muted)' }}>
          Arcitae Dedupe
        </span>
      }
      sidebar={
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          Folder nav — coming in T-015+
        </p>
      }
      contactSheet={
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          Contact sheet — coming in Stage 3
        </p>
      }
      inspector={
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          Inspector — coming in Stage 3
        </p>
      }
    />
  );
}

export default App;
