import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('renders initial count of 0', () => {
    render(<App />)
    expect(screen.getByText('Count: 0')).toBeInTheDocument()
  })

  it('increments count on click', async () => {
    render(<App />)
    await userEvent.click(screen.getByText('Increment'))
    expect(screen.getByText('Count: 1')).toBeInTheDocument()
  })

  it('decrements count on click', async () => {
    render(<App />)
    await userEvent.click(screen.getByText('Decrement'))
    expect(screen.getByText('Count: -1')).toBeInTheDocument()
  })

  it('resets count to 0', async () => {
    render(<App />)
    await userEvent.click(screen.getByText('Increment'))
    await userEvent.click(screen.getByText('Increment'))
    expect(screen.getByText('Count: 2')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Reset'))
    expect(screen.getByText('Count: 0')).toBeInTheDocument()
  })
})
