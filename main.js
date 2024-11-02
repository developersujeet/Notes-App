let body = document.querySelector('body');
let noteBox = document.querySelector("#input-note");
let btn = document.querySelector("#input-add");
const noteList = document.getElementById('notes-list');

document.querySelector('.input-box').addEventListener('submit', function(event) {
  event.preventDefault();
});

btn.addEventListener("click", () => {
  if (noteBox.value !== '' && noteBox.value.length >= 3) {
    addNotes();
  } else {
    alert("Too small! Cannot add.");
  }
  noteBox.value = "";
});

const addNotes = () => {
  let note = noteBox.value.trim();
  const notes = getNotes();
  notes.push({ note });
  saveNotes(notes);
  renderNotes();
};

const deleteNote = (index) => {
  const notes = getNotes();
  notes.splice(index, 1);
  saveNotes(notes);
  renderNotes();
};

const saveNotes = (notes) => {
  localStorage.setItem("notes", JSON.stringify(notes));
};

const getNotes = () => {
  return JSON.parse(localStorage.getItem("notes")) || [];
};

const renderNotes = () => {
  noteList.innerHTML = '';
  const notes = getNotes();
  notes.forEach((note, index) => {
    const div = document.createElement('div');
    div.innerHTML = `<div class="note-item">
    <button class="copy" data="${note.note}">📋</button>
      <p class="msgNote">${note.note}</p>
      <button class="delete" data-index="${index}">Delete</button>
    </div>`;
    noteList.appendChild(div);
  });

  document.querySelectorAll(".delete").forEach(button => {
    button.addEventListener("click", function() {
      const index = this.getAttribute("data-index");
      deleteNote(index);
    });
  });

  document.querySelectorAll(".copy").forEach(button2 => {
    button2.addEventListener("click", () => {
      const data = button2.getAttribute("data");
      writeToClipboard(data);
    });
  });
};

document.addEventListener("DOMContentLoaded", () => {
  loadNote();
});

const loadNote = () => {
  renderNotes();
};

const writeToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    alert("Text copied!");
  } catch (e) {
    alert(e);
  }
};