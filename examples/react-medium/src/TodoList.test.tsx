import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { TodoList } from './TodoList'

describe('TodoList', () => {
  it('renders empty list', () => {
    render(<TodoList />)
    expect(screen.getByText('Todo List')).toBeInTheDocument()
    expect(screen.getByRole('list')).toBeEmptyDOMElement()
  })

  it('can add todo', () => {
    render(<TodoList />)

    const input = screen.getByLabelText('New todo')
    fireEvent.change(input, { target: { value: 'Buy groceries' } })
    fireEvent.click(screen.getByText('Add'))

    expect(screen.getByText('Buy groceries')).toBeInTheDocument()
  })

  it('can toggle complete', () => {
    render(<TodoList />)

    const input = screen.getByLabelText('New todo')
    fireEvent.change(input, { target: { value: 'Walk the dog' } })
    fireEvent.click(screen.getByText('Add'))

    const toggle = screen.getByRole('button', { name: 'Toggle Walk the dog' })
    fireEvent.click(toggle)

    expect(toggle).toHaveStyle('text-decoration: line-through')

    fireEvent.click(toggle)
    expect(toggle).toHaveStyle('text-decoration: none')
  })

  it('can delete todo', () => {
    render(<TodoList />)

    const input = screen.getByLabelText('New todo')
    fireEvent.change(input, { target: { value: 'Clean house' } })
    fireEvent.click(screen.getByText('Add'))

    expect(screen.getByText('Clean house')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Delete Clean house' }))

    expect(screen.queryByText('Clean house')).not.toBeInTheDocument()
  })

  it('filters active todos', () => {
    render(<TodoList />)
    const input = screen.getByLabelText('New todo')

    fireEvent.change(input, { target: { value: 'Active task' } })
    fireEvent.click(screen.getByText('Add'))
    fireEvent.change(input, { target: { value: 'Done task' } })
    fireEvent.click(screen.getByText('Add'))

    // Complete the second todo
    fireEvent.click(screen.getByRole('button', { name: 'Toggle Done task' }))

    // Filter active
    fireEvent.click(screen.getByRole('button', { name: 'Filter active' }))

    expect(screen.getByText('Active task')).toBeInTheDocument()
    expect(screen.queryByText('Done task')).not.toBeInTheDocument()
  })

  it('filters completed todos', () => {
    render(<TodoList />)
    const input = screen.getByLabelText('New todo')

    fireEvent.change(input, { target: { value: 'Active task' } })
    fireEvent.click(screen.getByText('Add'))
    fireEvent.change(input, { target: { value: 'Done task' } })
    fireEvent.click(screen.getByText('Add'))

    fireEvent.click(screen.getByRole('button', { name: 'Toggle Done task' }))

    // Filter completed
    fireEvent.click(screen.getByRole('button', { name: 'Filter completed' }))

    expect(screen.queryByText('Active task')).not.toBeInTheDocument()
    expect(screen.getByText('Done task')).toBeInTheDocument()
  })
})
