# USSF Learning Center Certification API

The U.S. Soccer Federation provides a REST API through the Learning Center for verifying referee certifications and licenses.

## Base URL

```
https://connect.learning.ussoccer.com/certifications
```

## Endpoints

### GET /users

Look up a referee's 16-digit USSF ID by email address.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| email     | Yes      | The email address associated with the referee's USSF account |

**Response (200):**
```json
{
  "ussf_id": "1234567890123456"
}
```

**Response (404):** Returned when no USSF account is found for the given email.

### GET /licenses/{ussf_id}

Retrieve the list of active licenses/certifications for a referee.

**Path Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| ussf_id   | Yes      | The 16-digit USSF ID |

**Response (200):**
```json
{
  "ussf_id": "1234567890123456",
  "licenses": [
    {
      "license_id": "1",
      "discipline": "referee",
      "status": "active",
      "issue_date": "2024-01-15",
      "expiration_date": "2025-01-15",
      "issuer": "US Soccer",
      "id_association": "OSSR"
    }
  ]
}
```

Each license record contains:
| Field           | Description |
|-----------------|-------------|
| license_id      | Numeric identifier for the license level within its discipline |
| discipline      | The discipline category (e.g., referee, futsal, assignor) |
| status          | License status (active, expired, revoked) |
| issue_date      | Date the license was issued (YYYY-MM-DD) |
| expiration_date | Date the license expires (YYYY-MM-DD) |
| issuer          | The organization that issued the license |
| id_association  | The state association identifier |

## License ID Reference

To look up detailed information about a license, concatenate the `discipline` and `license_id` fields with an underscore separator (e.g., discipline `"referee"` + license_id `"1"` = `"referee_1"`). Use the resulting identifier with the tables below.

### Referee Licenses

| ID         | Name                  | Discipline | Rank | Pathway    |
|------------|-----------------------|------------|------|------------|
| referee_1  | Grassroots Referee    | Referee    | 8    | Grassroots |
| referee_2  | Regional Referee      | Referee    | 7    | Regional   |
| referee_3  | Advanced Regional Referee | Referee | 6   | Regional   |
| referee_4  | National 2 Referee    | Referee    | 5    | National   |
| referee_5  | National 1 Referee    | Referee    | 4    | National   |
| referee_6  | National Referee      | Referee    | 3    | National   |
| referee_7  | Professional Referee  | Referee    | 2    | Professional |
| referee_8  | FIFA Referee          | Referee    | 1    | FIFA       |

### Futsal Licenses

| ID        | Name                       | Discipline | Rank | Pathway    |
|-----------|----------------------------|------------|------|------------|
| futsal_1  | Grassroots Futsal Referee  | Futsal     | 4    | Grassroots |
| futsal_2  | Advanced Futsal Referee    | Futsal     | 3    | Regional   |
| futsal_3  | National Futsal Referee    | Futsal     | 2    | National   |
| futsal_4  | FIFA Futsal Referee        | Futsal     | 1    | FIFA       |

### Assignor Licenses

| ID          | Name                | Discipline | Rank | Pathway    |
|-------------|---------------------|------------|------|------------|
| assignor_1  | Grassroots Assignor | Assignor   | 3    | Grassroots |
| assignor_2  | Regional Assignor   | Assignor   | 2    | Regional   |
| assignor_3  | National Assignor   | Assignor   | 1    | National   |

### Assessor Licenses

| ID          | Name                | Discipline | Rank | Pathway    |
|-------------|---------------------|------------|------|------------|
| assessor_1  | Grassroots Assessor | Assessor   | 3    | Grassroots |
| assessor_2  | Regional Assessor   | Assessor   | 2    | Regional   |
| assessor_3  | National Assessor   | Assessor   | 1    | National   |

### Instructor Licenses

| ID            | Name                  | Discipline  | Rank | Pathway    |
|---------------|-----------------------|-------------|------|------------|
| instructor_1  | Grassroots Instructor | Instructor  | 3    | Grassroots |
| instructor_2  | Regional Instructor   | Instructor  | 2    | Regional   |
| instructor_3  | National Instructor   | Instructor  | 1    | National   |

### Mentor Licenses

| ID        | Name              | Discipline | Rank | Pathway    |
|-----------|-------------------|------------|------|------------|
| mentor_1  | Grassroots Mentor | Mentor     | 3    | Grassroots |
| mentor_2  | Regional Mentor   | Mentor     | 2    | Regional   |
| mentor_3  | National Mentor   | Mentor     | 1    | National   |
