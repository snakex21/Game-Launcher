package chatserver

import (
	"database/sql"
	"encoding/json"
	"errors"
	"strings"
	"unicode/utf8"
)

// Message is a message as sent to clients.
type Message struct {
	ID         int64       `json:"id"`
	SenderID   int64       `json:"sender_id"`
	Sender     string      `json:"sender"`
	ReceiverID int64       `json:"receiver_id,omitempty"`
	RoomID     int64       `json:"room_id,omitempty"`
	Content    string      `json:"content"`
	Timestamp  string      `json:"timestamp"`
	Edited     bool        `json:"edited"`
	ReplyTo    int64       `json:"reply_to,omitempty"`
	Attachment *Attachment `json:"attachment,omitempty"`
	Read       bool        `json:"read"`
	Deleted    bool        `json:"deleted"`
}

// Attachment of a message.
type Attachment struct {
	ServerFilename   string `json:"server_filename"`
	OriginalFilename string `json:"original_filename"`
	Mimetype         string `json:"mimetype"`
}

// Room for clients.
type Room struct {
	ID      int64  `json:"id"`
	Name    string `json:"name"`
	Locked  bool   `json:"locked"`
	Members int    `json:"members"`
	Member  bool   `json:"member"`
}

const msgSelect = `SELECT m.id, COALESCE(m.sender_id,0), COALESCE(u.username,'(usunięty)'), COALESCE(m.receiver_id,0), COALESCE(m.room_id,0),
	COALESCE(m.content,''), CAST(m.timestamp AS TEXT), m.edited_at IS NOT NULL, COALESCE(m.replied_to_message_id,0),
	COALESCE(m.attachment_server_filename,''), COALESCE(m.attachment_original_filename,''), COALESCE(m.attachment_mimetype,''),
	m.is_read_by_receiver, m.is_deleted
	FROM message m LEFT JOIN user u ON u.id = m.sender_id `

func scanMessages(rows *sql.Rows) ([]Message, error) {
	defer rows.Close()
	out := []Message{}
	for rows.Next() {
		var m Message
		var sf, of, mt string
		if err := rows.Scan(&m.ID, &m.SenderID, &m.Sender, &m.ReceiverID, &m.RoomID, &m.Content, &m.Timestamp, &m.Edited, &m.ReplyTo, &sf, &of, &mt, &m.Read, &m.Deleted); err != nil {
			return nil, err
		}
		if sf != "" && !m.Deleted {
			m.Attachment = &Attachment{sf, of, mt}
		}
		if m.Deleted {
			m.Content = ""
		}
		out = append(out, m)
	}
	return out, rows.Err()
}

func (s *Server) messageByID(id int64) (*Message, error) {
	rows, err := s.DB.Query(msgSelect+`WHERE m.id = ?`, id)
	if err != nil {
		return nil, err
	}
	list, err := scanMessages(rows)
	if err != nil || len(list) == 0 {
		return nil, errors.New("nie ma takiej wiadomości")
	}
	return &list[0], nil
}

func (s *Server) isMember(userID, roomID int64) bool {
	var n int
	_ = s.DB.QueryRow(`SELECT COUNT(*) FROM room_membership WHERE user_id = ? AND room_id = ?`, userID, roomID).Scan(&n)
	return n > 0
}

func (s *Server) blockedEither(a, b int64) bool {
	var n int
	_ = s.DB.QueryRow(`SELECT COUNT(*) FROM blocked_relationship WHERE (blocker_id = ?1 AND blocked_id = ?2) OR (blocker_id = ?2 AND blocked_id = ?1)`, a, b).Scan(&n)
	return n > 0
}

func (s *Server) rooms(userID int64) ([]Room, error) {
	rows, err := s.DB.Query(`SELECT r.id, r.name, COALESCE(r.password_hash,'') <> '',
		(SELECT COUNT(*) FROM room_membership m WHERE m.room_id = r.id),
		EXISTS(SELECT 1 FROM room_membership m WHERE m.room_id = r.id AND m.user_id = ?)
		FROM chat_room r ORDER BY r.name COLLATE NOCASE`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []Room{}
	for rows.Next() {
		var r Room
		if err := rows.Scan(&r.ID, &r.Name, &r.Locked, &r.Members, &r.Member); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

type userRow struct {
	User
	Blocked   bool `json:"blocked"`
	BlockedMe bool `json:"blocked_me"`
	Unread    int  `json:"unread"`
}

func (s *Server) users(me int64) ([]userRow, error) {
	rows, err := s.DB.Query(`SELECT u.id, u.username, u.is_admin,
		EXISTS(SELECT 1 FROM blocked_relationship b WHERE b.blocker_id = ?1 AND b.blocked_id = u.id),
		EXISTS(SELECT 1 FROM blocked_relationship b WHERE b.blocker_id = u.id AND b.blocked_id = ?1),
		(SELECT COUNT(*) FROM message m WHERE m.sender_id = u.id AND m.receiver_id = ?1 AND m.is_read_by_receiver = 0 AND m.is_deleted = 0)
		FROM user u WHERE u.id <> ?1 AND u.is_banned = 0 ORDER BY u.username COLLATE NOCASE`, me)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []userRow{}
	for rows.Next() {
		var r userRow
		if err := rows.Scan(&r.ID, &r.Username, &r.Admin, &r.Blocked, &r.BlockedMe, &r.Unread); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	rows.Close()
	for i := range out {
		out[i].Online = s.online(out[i].ID)
	}
	return out, nil
}

// deliver sends an event to every socket of the users concerned by a message.
func (s *Server) deliver(m *Message, typ string, payload any) {
	s.each(func(c *client) {
		switch {
		case m.RoomID != 0:
			if s.isMember(c.user.ID, m.RoomID) {
				c.emit(typ, payload)
			}
		default:
			if c.user.ID == m.SenderID || c.user.ID == m.ReceiverID {
				c.emit(typ, payload)
			}
		}
	})
}

func decode(raw json.RawMessage, v any) error {
	if len(raw) == 0 {
		raw = []byte("{}")
	}
	if err := json.Unmarshal(raw, v); err != nil {
		return errors.New("nieprawidłowe dane zdarzenia")
	}
	return nil
}

func cleanContent(s string) (string, error) {
	s = strings.TrimSpace(strings.ToValidUTF8(s, "�"))
	if utf8.RuneCountInString(s) > MaxMessageRunes {
		return "", errors.New("wiadomość jest za długa (maks. 4000 znaków)")
	}
	return s, nil
}

func (s *Server) handle(c *client, in inbound) error {
	me := c.user.ID
	reply := func(typ string, data any) { c.emitID(typ, in.ID, data) }
	switch in.Type {
	case "ping":
		reply("pong", nil)
	case "list_rooms":
		r, err := s.rooms(me)
		if err != nil {
			return err
		}
		reply("rooms", r)
	case "list_users":
		u, err := s.users(me)
		if err != nil {
			return err
		}
		reply("users", u)
	case "create_room":
		var d struct{ Name, Password string }
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		d.Name = strings.TrimSpace(d.Name)
		if l := utf8.RuneCountInString(d.Name); l < 2 || l > 60 {
			return errors.New("nazwa pokoju: 2–60 znaków")
		}
		var ph any
		if d.Password != "" {
			h, err := HashPassword(d.Password)
			if err != nil {
				return err
			}
			ph = h
		}
		res, err := s.DB.Exec(`INSERT INTO chat_room(name, creator_id, password_hash) VALUES (?, ?, ?)`, d.Name, me, ph)
		if err != nil {
			return errors.New("pokój o tej nazwie już istnieje")
		}
		id, _ := res.LastInsertId()
		_, _ = s.DB.Exec(`INSERT OR IGNORE INTO room_membership(user_id, room_id) VALUES (?, ?)`, me, id)
		s.each(func(x *client) { x.emit("rooms_changed", nil) })
		return s.joinRoom(c, in.ID, id, "")
	case "join_specific_room":
		var d struct {
			RoomID   int64  `json:"room_id"`
			Password string `json:"password"`
		}
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		return s.joinRoom(c, in.ID, d.RoomID, d.Password)
	case "leave_room":
		var d struct {
			RoomID int64 `json:"room_id"`
		}
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		_, _ = s.DB.Exec(`DELETE FROM room_membership WHERE user_id = ? AND room_id = ?`, me, d.RoomID)
		c.mu.Lock()
		delete(c.rooms, d.RoomID)
		c.mu.Unlock()
		reply("room_left", map[string]int64{"room_id": d.RoomID})
		s.each(func(x *client) { x.emit("rooms_changed", nil) })
	case "history":
		var d struct {
			RoomID   int64 `json:"room_id"`
			UserID   int64 `json:"user_id"`
			BeforeID int64 `json:"before_id"`
		}
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		msgs, err := s.history(me, d.RoomID, d.UserID, d.BeforeID)
		if err != nil {
			return err
		}
		reply("history", map[string]any{"room_id": d.RoomID, "user_id": d.UserID, "messages": msgs})
	case "send_message":
		var d struct {
			RoomID     int64       `json:"room_id"`
			ToUserID   int64       `json:"to_user_id"`
			Content    string      `json:"content"`
			ReplyTo    int64       `json:"reply_to"`
			Attachment *Attachment `json:"attachment"`
		}
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		content, err := cleanContent(d.Content)
		if err != nil {
			return err
		}
		if content == "" && d.Attachment == nil {
			return errors.New("pusta wiadomość")
		}
		var room, to any
		switch {
		case d.RoomID != 0 && d.ToUserID == 0:
			if !s.isMember(me, d.RoomID) {
				return errors.New("nie jesteś członkiem tego pokoju")
			}
			room = d.RoomID
		case d.ToUserID != 0 && d.RoomID == 0:
			if d.ToUserID == me {
				return errors.New("nie można pisać do siebie")
			}
			if s.blockedEither(me, d.ToUserID) {
				return errors.New("nie można wysłać wiadomości (blokada)")
			}
			if _, err := s.userByID(d.ToUserID); err != nil {
				return errors.New("nie ma takiego użytkownika")
			}
			to = d.ToUserID
		default:
			return errors.New("podaj pokój albo odbiorcę")
		}
		var sf, of, mt any
		if a := d.Attachment; a != nil {
			if len(a.ServerFilename) > 64 || strings.ContainsAny(a.ServerFilename, `/\:`) || a.ServerFilename == "" {
				return errors.New("nieprawidłowy załącznik")
			}
			sf, of, mt = a.ServerFilename, a.OriginalFilename, a.Mimetype
		}
		var reply2 any
		if d.ReplyTo != 0 {
			reply2 = d.ReplyTo
		}
		res, err := s.DB.Exec(`INSERT INTO message(sender_id, receiver_id, room_id, content, replied_to_message_id,
			attachment_server_filename, attachment_original_filename, attachment_mimetype) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
			me, to, room, content, reply2, sf, of, mt)
		if err != nil {
			return err
		}
		id, _ := res.LastInsertId()
		m, err := s.messageByID(id)
		if err != nil {
			return err
		}
		reply("sent", map[string]int64{"message_id": id})
		s.deliver(m, "message", m)
	case "edit_message", "delete_message":
		var d struct {
			ID      int64  `json:"message_id"`
			Content string `json:"content"`
		}
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		m, err := s.messageByID(d.ID)
		if err != nil {
			return err
		}
		if m.Deleted {
			return errors.New("wiadomość została usunięta")
		}
		if m.SenderID != me && !(in.Type == "delete_message" && c.user.Admin) {
			return errors.New("możesz zmieniać tylko swoje wiadomości")
		}
		if in.Type == "edit_message" {
			content, err := cleanContent(d.Content)
			if err != nil || content == "" {
				if err == nil {
					err = errors.New("pusta wiadomość")
				}
				return err
			}
			_, err = s.DB.Exec(`UPDATE message SET content = ?, edited_at = CURRENT_TIMESTAMP WHERE id = ?`, content, d.ID)
			if err != nil {
				return err
			}
			m, _ = s.messageByID(d.ID)
			s.deliver(m, "message_edited", m)
		} else {
			if _, err := s.DB.Exec(`UPDATE message SET is_deleted = 1, content = NULL WHERE id = ?`, d.ID); err != nil {
				return err
			}
			s.deliver(m, "message_deleted", map[string]int64{"message_id": d.ID, "room_id": m.RoomID})
		}
	case "typing":
		var d struct {
			RoomID   int64 `json:"room_id"`
			ToUserID int64 `json:"to_user_id"`
			On       bool  `json:"on"`
		}
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		ev := map[string]any{"user_id": me, "username": c.user.Username, "room_id": d.RoomID, "on": d.On}
		s.each(func(x *client) {
			if x.user.ID == me {
				return
			}
			if (d.RoomID != 0 && s.isMember(x.user.ID, d.RoomID)) || (d.RoomID == 0 && x.user.ID == d.ToUserID && !s.blockedEither(me, d.ToUserID)) {
				x.emit("typing", ev)
			}
		})
	case "mark_read":
		var d struct {
			FromUserID int64 `json:"from_user_id"`
		}
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		if _, err := s.DB.Exec(`UPDATE message SET is_read_by_receiver = 1 WHERE sender_id = ? AND receiver_id = ? AND is_read_by_receiver = 0`, d.FromUserID, me); err != nil {
			return err
		}
		s.each(func(x *client) {
			if x.user.ID == d.FromUserID {
				x.emit("read", map[string]int64{"reader_id": me})
			}
		})
	case "block":
		var d struct {
			UserID int64 `json:"user_id"`
			On     bool  `json:"on"`
		}
		if err := decode(in.Data, &d); err != nil {
			return err
		}
		if d.UserID == me {
			return errors.New("nie można zablokować siebie")
		}
		var err error
		if d.On {
			_, err = s.DB.Exec(`INSERT OR IGNORE INTO blocked_relationship(blocker_id, blocked_id) VALUES (?, ?)`, me, d.UserID)
		} else {
			_, err = s.DB.Exec(`DELETE FROM blocked_relationship WHERE blocker_id = ? AND blocked_id = ?`, me, d.UserID)
		}
		if err != nil {
			return err
		}
		reply("blocked", map[string]any{"user_id": d.UserID, "on": d.On})
	default:
		return errors.New("nieznane zdarzenie: " + in.Type)
	}
	return nil
}

func (s *Server) joinRoom(c *client, reqID, roomID int64, password string) error {
	var name string
	var hash sql.NullString
	if err := s.DB.QueryRow(`SELECT name, password_hash FROM chat_room WHERE id = ?`, roomID).Scan(&name, &hash); err != nil {
		return errors.New("nie ma takiego pokoju")
	}
	me := c.user.ID
	if !s.isMember(me, roomID) {
		if hash.Valid && hash.String != "" {
			if ok, _ := CheckPassword(hash.String, password); !ok {
				return errors.New("nieprawidłowe hasło pokoju")
			}
		}
		if _, err := s.DB.Exec(`INSERT OR IGNORE INTO room_membership(user_id, room_id) VALUES (?, ?)`, me, roomID); err != nil {
			return err
		}
		s.each(func(x *client) { x.emit("rooms_changed", nil) })
	}
	c.mu.Lock()
	c.rooms[roomID] = true
	c.mu.Unlock()
	msgs, err := s.history(me, roomID, 0, 0)
	if err != nil {
		return err
	}
	var members []User
	rows, err := s.DB.Query(`SELECT u.id, u.username, u.is_admin FROM room_membership m JOIN user u ON u.id = m.user_id WHERE m.room_id = ? ORDER BY u.username COLLATE NOCASE`, roomID)
	if err == nil {
		for rows.Next() {
			var u User
			if rows.Scan(&u.ID, &u.Username, &u.Admin) == nil {
				members = append(members, u)
			}
		}
		rows.Close()
		for i := range members {
			members[i].Online = s.online(members[i].ID)
		}
	}
	c.emitID("room_joined", reqID, map[string]any{"room": map[string]any{"id": roomID, "name": name}, "members": members, "messages": msgs})
	return nil
}

// history returns up to 50 messages before beforeID (oldest first).
func (s *Server) history(me, roomID, userID, beforeID int64) ([]Message, error) {
	if beforeID <= 0 {
		beforeID = 1 << 62
	}
	var rows *sql.Rows
	var err error
	switch {
	case roomID != 0:
		if !s.isMember(me, roomID) {
			return nil, errors.New("nie jesteś członkiem tego pokoju")
		}
		rows, err = s.DB.Query(msgSelect+`WHERE m.room_id = ? AND m.id < ? ORDER BY m.id DESC LIMIT ?`, roomID, beforeID, historyPage)
	case userID != 0:
		rows, err = s.DB.Query(msgSelect+`WHERE m.room_id IS NULL AND ((m.sender_id = ?1 AND m.receiver_id = ?2) OR (m.sender_id = ?2 AND m.receiver_id = ?1)) AND m.id < ?3 ORDER BY m.id DESC LIMIT ?4`, me, userID, beforeID, historyPage)
	default:
		return nil, errors.New("podaj pokój albo użytkownika")
	}
	if err != nil {
		return nil, err
	}
	list, err := scanMessages(rows)
	if err != nil {
		return nil, err
	}
	for i, j := 0, len(list)-1; i < j; i, j = i+1, j-1 {
		list[i], list[j] = list[j], list[i]
	}
	return list, nil
}
