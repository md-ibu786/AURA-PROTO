import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ExplorerPage from './pages/ExplorerPage'

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/*" element={<ExplorerPage />} />
            </Routes>
        </BrowserRouter>
    )
}

export default App
