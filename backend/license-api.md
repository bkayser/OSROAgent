# USSF License Lookup API

Public REST API for looking up U.S. Soccer Federation (USSF) certifications and licenses. Used by US Soccer Connect (Learning) for referee, coach, and safety credentials.

**Base URL:** `https://connect.learning.ussoccer.com/certifications/public`

**Authentication:** None. All endpoints are public.

---

## Endpoints

### List license types (catalog)

Returns the catalog of license types. Use the returned `license_id` and related fields to interpret responses from the user-licenses endpoint.

| Method | Path |
|--------|------|
| GET | `/licenses` |

**Full URL:** `https://connect.learning.ussoccer.com/certifications/public/licenses`

**Response:** Array of license-type objects (structure not documented here). For a human-readable reference of license IDs and types, see [License ID reference](#license-id-reference) below.

---

### Look up users by email

Find one or more users by email address. Returns USSF ID, full name, and under-18 flag.

| Method | Path |
|--------|------|
| GET | `/users` |

**Query parameters**

| Name   | Type   | Required | Description                    |
|--------|--------|----------|--------------------------------|
| `email` | string | Yes      | Email address to search for.  |

**Response:** `200 OK` — JSON array of user objects.

| Field        | Type    | Description                          |
|-------------|---------|--------------------------------------|
| `ussf_id`   | string  | 16-digit USSF ID (no dashes).        |
| `full_name` | string  | Full name of the user.               |
| `is_under18`| boolean | Whether the user is under 18.        |

**Example request**

```http
GET /certifications/public/users?email=bill@kayser.org
Host: connect.learning.ussoccer.com
```

```bash
curl 'https://connect.learning.ussoccer.com/certifications/public/users?email=bill@kayser.org'
```

**Example response**

```json
[
  {
    "is_under18": false,
    "ussf_id": "2018000004076044",
    "full_name": "Bill Kayser"
  }
]
```

---

### Look up users by name and state

Find users by first name, last name, and state. Returns USSF ID and under-18 flag only; `full_name` is not returned.

| Method | Path |
|--------|------|
| GET | `/users` |

**Query parameters**

| Name         | Type   | Required | Description                    |
|--------------|--------|----------|--------------------------------|
| `first_name` | string | Yes      | First name.                    |
| `last_name`  | string | Yes      | Last name.                     |
| `state`      | string | Yes      | Two-letter state code (e.g. OR). |

**Response:** `200 OK` — JSON array of user objects.

| Field        | Type    | Description                          |
|-------------|---------|--------------------------------------|
| `ussf_id`   | string  | 16-digit USSF ID (no dashes).        |
| `full_name` | null    | Not returned for this query.         |
| `is_under18`| boolean | Whether the user is under 18.        |

**Example request**

```http
GET /certifications/public/users?first_name=Elliott&last_name=Kayser&state=OR
Host: connect.learning.ussoccer.com
```

```bash
curl 'https://connect.learning.ussoccer.com/certifications/public/users?first_name=Elliott&last_name=Kayser&state=OR'
```

**Example response**

```json
[
  {
    "is_under18": false,
    "ussf_id": "1000000001910026",
    "full_name": null
  }
]
```

---

### Get licenses for a user (by USSF ID)

Returns all certifications/licenses for a single user identified by USSF ID. Use this after resolving a user via the email or name+state endpoints.

| Method | Path |
|--------|------|
| GET | `/users/{ussf_id}/user-licenses` |

**Path parameters**

| Name      | Type   | Description                              |
|-----------|--------|------------------------------------------|
| `ussf_id` | string | 16-digit USSF ID with no dashes or spaces. |

**Response:** `200 OK` — JSON array of license/certification records.

| Field             | Type    | Description                                      |
|-------------------|---------|--------------------------------------------------|
| `license_id`      | integer | ID of the license type (see [License ID reference](#license-id-reference)). |
| `discipline`      | string  | `"coach"`, `"referee"`, or `"safety"`.           |
| `issue_date`      | string  | Date issued (YYYY-MM-DD).                        |
| `expiration_date` | string \| null | Expiration (YYYY-MM-DD), or null if no expiration. |
| `issuer`          | string  | Issuing organization name.                       |
| `is_batch_upload`  | boolean | Whether the record was batch-uploaded.           |
| `ignore_compliance` | boolean | Whether compliance is ignored for this record. |
| `id_association`  | integer | ID of the issuing association.                   |

**Example request**

```http
GET /certifications/public/users/2018000004076044/user-licenses
Host: connect.learning.ussoccer.com
```

```bash
curl 'https://connect.learning.ussoccer.com/certifications/public/users/2018000004076044/user-licenses'
```

**Example response**

```json
[
  {
    "license_id": 1,
    "discipline": "coach",
    "issue_date": "2017-08-07",
    "expiration_date": null,
    "issuer": "U.S. Soccer",
    "is_batch_upload": false,
    "ignore_compliance": false,
    "id_association": 1
  },
  {
    "license_id": 8,
    "discipline": "referee",
    "issue_date": "2026-01-03",
    "expiration_date": "2026-12-31",
    "issuer": "Oregon State Referee Committee",
    "is_batch_upload": false,
    "ignore_compliance": false,
    "id_association": 10000041
  },
  {
    "license_id": 1,
    "discipline": "safety",
    "issue_date": "2025-06-04",
    "expiration_date": "2026-06-04",
    "issuer": "U.S. Center for SafeSport",
    "is_batch_upload": false,
    "ignore_compliance": false,
    "id_association": 1
  }
]
```

---

## License ID reference

Use these tables to map `license_id` and `discipline` from the user-licenses response to a human-readable license name and type. The `/licenses` endpoint returns the authoritative catalog; this section is a convenience reference.

### Instructor licenses (coach)

| Name | License ID | Discipline | Rank | Type |
|------|------------|------------|------|------|
| Coach Educator Pro | coach_41 | coach | 1 | coach_coach_instructor |
| Educator Developer | coach_44 | coach | 2 | coach_coach_instructor |
| Coach Educator A | coach_32 | coach | 3 | coach_coach_instructor |
| Coach Educator B | coach_31 | coach | 4 | coach_coach_instructor |
| Coach Educator C | coach_30 | coach | 5 | coach_coach_instructor |
| Coach Educator D License | coach_34 | coach | 6 | coach_coach_instructor |
| Coach Educator Grassroots | coach_33 | coach | 7 | coach_coach_instructor |
| Educator-Club Technical Leadership Level 1 | coach_35 | coach | 8 | coach_coach_instructor |
| Coach Educator Goalkeeper C | coach_40 | coach | 9 | coach_coach_instructor |
| Grassroots Instructor License Level 1 | coach_17 | coach | 10 | coach_coach_instructor |
| Grassroots Instructor License Level 2 | coach_29 | coach | 11 | coach_coach_instructor |
| Club Technical Leadership: Level 3 | coach_39 | coach | 1 | coach_coach_leadership |
| Club Technical Leadership: Level 2 | coach_38 | coach | 2 | coach_coach_leadership |
| Club Technical Leadership: Level 1 | coach_37 | coach | 3 | coach_coach_leadership |
| Academy Director | coach_7 | coach | 4 | coach_coach_leadership |
| Director of Coaching | coach_28 | coach | 5 | coach_coach_leadership |

### Coaching licenses (pathway and supplemental)

| Name | License ID | Discipline | Rank | Type |
|------|------------|------------|------|------|
| Pro License | coach_16 | coach | 1 | coach_pathway |
| A - Senior | coach_15 | coach | 3 | coach_pathway |
| A - Youth | coach_14 | coach | 4 | coach_pathway |
| National A | coach_6 | coach | 5 | coach_pathway |
| National B | coach_5 | coach | 6 | coach_pathway |
| National C | coach_4 | coach | 7 | coach_pathway |
| National D | coach_3 | coach | 8 | coach_pathway |
| National E | coach_2 | coach | 9 | coach_pathway |
| 11v11 License (in-person) | coach_25 | coach | 10 | coach_pathway |
| 9v9 License (in-person) | coach_24 | coach | 11 | coach_pathway |
| 7v7 License (in-person) | coach_23 | coach | 12 | coach_pathway |
| 4v4 License (in-person) | coach_22 | coach | 13 | coach_pathway |
| 11v11 License (online) | coach_21 | coach | 14 | coach_pathway |
| 9v9 License (online) | coach_20 | coach | 15 | coach_pathway |
| 7v7 License (online) | coach_19 | coach | 16 | coach_pathway |
| 4v4 License (online) | coach_18 | coach | 17 | coach_pathway |
| National F | coach_1 | coach | 18 | coach_pathway |
| Talent Scout: Level 2 | coach_36 | coach | 1 | coach_supplemental |
| Talent Scout | coach_27 | coach | 2 | coach_supplemental |
| Goalkeeper A | coach_26 | coach | 3 | coach_supplemental |
| Goalkeeper B | coach_43 | coach | 4 | coach_supplemental |
| Goalkeeper C | coach_42 | coach | 5 | coach_supplemental |
| National Goalkeeping | coach_9 | coach | 6 | coach_supplemental |
| National Youth License | coach_10 | coach | 7 | coach_supplemental |

### Referee instructors, assessors, assignors

| Name | License ID | Discipline | Rank | Type |
|------|------------|------------|------|------|
| National Assessor | referee_31 | referee | 1 | referee_assessor |
| Regional Assessor | referee_19 | referee | 2 | referee_assessor |
| Grassroots Assessor | referee_20 | referee | 3 | referee_assessor |
| PRO Assignor | referee_46 | referee | 1 | referee_assignor |
| National Assignor | referee_17 | referee | 2 | referee_assignor |
| Assignor | referee_18 | referee | 3 | referee_assignor |
| National Referee Coach | referee_9 | referee | 1 | referee_educator |
| Referee Coach | referee_10 | referee | 2 | referee_educator |
| Referee Mentor + | referee_47 | referee | 3 | referee_educator |
| Referee Mentor | referee_37 | referee | 4 | referee_educator |
| National Emeritus Referee | referee_15 | referee | 1 | referee_emeritus |
| Regional Emeritus Referee | referee_16 | referee | 2 | referee_emeritus |
| FIFA Futsal Referee | referee_11 | referee | 1 | referee_futsal |
| Regional Futsal Referee | referee_12 | referee | 2 | referee_futsal |
| Grassroots Futsal Referee | referee_29 | referee | 3 | referee_futsal |
| National Instructor | referee_32 | referee | 1 | referee_instructor |
| Regional Instructor | referee_21 | referee | 2 | referee_instructor |
| Grassroots Instructor | referee_22 | referee | 3 | referee_instructor |

### Referee licenses (pathway and specialist)

| Name | License ID | Discipline | Rank | Type |
|------|------------|------------|------|------|
| FIFA Referee | referee_1 | referee | 1 | referee_pathway |
| FIFA Assistant Referee | referee_2 | referee | 2 | referee_pathway |
| PRO Referee | referee_3 | referee | 3 | referee_pathway |
| PRO Assistant Referee | referee_4 | referee | 4 | referee_pathway |
| National Referee | referee_5 | referee | 5 | referee_pathway |
| PRO 2 Referee | referee_40 | referee | 5 | referee_pathway |
| PRO 2 Assistant Referee | referee_41 | referee | 6 | referee_pathway |
| National Assistant Referee | referee_6 | referee | 6 | referee_pathway |
| Regional Referee | referee_7 | referee | 7 | referee_pathway |
| Referee | referee_8 | referee | 10 | referee_pathway |
| Armed Forces Referee Achievement | referee_44 | referee | 11 | referee_pathway |
| Digital Referee | referee_45 | referee | 12 | referee_pathway |
| FIFA VMO | referee_39 | referee | 1 | referee_specialist |
| Beach Soccer Referee | referee_13 | referee | 2 | referee_specialist |
| VMO | referee_42 | referee | 2 | referee_specialist |
| Indoor Soccer Referee | referee_14 | referee | 2 | referee_specialist |
| VAR/AVAR | referee_38 | referee | 2 | referee_specialist |
| PRO 2 VMO | referee_43 | referee | 3 | referee_specialist |

### Safety / compliance

| Name | License ID | Discipline | Rank | Type |
|------|------------|------------|------|------|
| SafeSport Trained | safety_1 | safety | 1 | safety_compliance |
| Background Check: Clear | safety_2 | safety | 1 | safety_compliance |
| Introduction to Safe... | safety_3 | safety | 1 | safety_medical |
| Safe Soccer Cleared | safety_6 | safety | 1 | safety_safe_soccer |
| Safe Soccer Phase 2 | safety_5 | safety | 2 | safety_safe_soccer |
| Safe Soccer Phase 1 | safety_4 | safety | 3 | safety_safe_soccer |

**Note:** The user-licenses endpoint returns numeric `license_id` values (e.g. `1`, `8`, `18`). The catalog at `/licenses` and the License ID reference above use string identifiers (e.g. `coach_41`, `referee_8`). You may need to call `/licenses` or maintain a mapping from numeric IDs to these names for display.
