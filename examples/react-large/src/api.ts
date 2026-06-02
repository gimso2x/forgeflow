export interface Item {
  id: number;
  name: string;
  status: string;
}

let nextId = 3;
let items: Item[] = [
  { id: 1, name: "Alpha", status: "active" },
  { id: 2, name: "Beta", status: "inactive" },
];

// Reset for tests
export function _resetItems() {
  nextId = 3;
  items = [
    { id: 1, name: "Alpha", status: "active" },
    { id: 2, name: "Beta", status: "inactive" },
  ];
}

export async function fetchItems(): Promise<Item[]> {
  return [...items];
}

export async function addItem(item: Omit<Item, "id">): Promise<Item> {
  const newItem: Item = { id: nextId++, ...item };
  items.push(newItem);
  return newItem;
}

export async function updateItem(
  id: number,
  updates: Omit<Item, "id">,
): Promise<Item | undefined> {
  const idx = items.findIndex((i) => i.id === id);
  if (idx === -1) return undefined;
  items[idx] = { id, ...updates };
  return items[idx];
}

export async function deleteItem(id: number): Promise<boolean> {
  const idx = items.findIndex((i) => i.id === id);
  if (idx === -1) return false;
  items.splice(idx, 1);
  return true;
}
