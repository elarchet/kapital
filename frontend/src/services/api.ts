/**
 * Kapital Decoupled REST API Client Service
 */

const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('kapital_token');
  if (token) {
    return { 'Authorization': `Bearer ${token}` };
  }
  return {};
};

export interface APIError {
  detail: string | Array<{ msg: string; loc: string[] }>;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('kapital_token');
      // Redirect to login if in browser environment
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    let errorData: APIError;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: 'An unexpected error occurred.' };
    }
    const message = typeof errorData.detail === 'string'
      ? errorData.detail
      : Array.isArray(errorData.detail)
      ? errorData.detail.map(d => d.msg).join(', ')
      : 'API Error';
    throw new Error(message);
  }

  // Handle No Content / Empty response
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Authentication
  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const formData = new URLSearchParams();
    formData.append('username', email); // OAuth2 password flow expects "username" field mapped to email
    formData.append('password', password);

    const response = await fetch('/api/auth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    if (!response.ok) {
      let errorMsg = 'Invalid email or password.';
      try {
        const errorData = await response.json();
        if (errorData?.detail) errorMsg = errorData.detail;
      } catch {}
      throw new Error(errorMsg);
    }

    const data = await response.json();
    localStorage.setItem('kapital_token', data.access_token);
    localStorage.setItem('kapital_user_email', email);
    return data;
  },

  logout() {
    localStorage.removeItem('kapital_token');
    localStorage.removeItem('kapital_user_email');
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  },

  getCurrentUserEmail(): string {
    return localStorage.getItem('kapital_user_email') || 'User';
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('kapital_token');
  },

  // Portfolios CRUD
  async getPortfolios(): Promise<any[]> {
    return request<any[]>('/api/portfolios/');
  },

  async getPortfolio(id: number): Promise<any> {
    return request<any>(`/api/portfolios/${id}`);
  },

  async createPortfolio(name: string, description: string = ''): Promise<any> {
    return request<any>('/api/portfolios/', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
  },

  async updatePortfolio(id: number, name: string, description: string = ''): Promise<any> {
    return request<any>(`/api/portfolios/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, description }),
    });
  },

  async deletePortfolio(id: number): Promise<any> {
    return request<any>(`/api/portfolios/${id}`, {
      method: 'DELETE',
    });
  },

  // Positions CRUD
  async getPositions(portfolioId?: number): Promise<any[]> {
    const url = portfolioId !== undefined ? `/api/positions/?portfolio_id=${portfolioId}` : '/api/positions/';
    return request<any[]>(url);
  },

  async createPosition(data: {
    portfolio_id: number;
    asset_type: string;
    ticker?: string;
    name: string;
    isin?: string;
    quantity: number;
    currency: string;
  }): Promise<any> {
    return request<any>('/api/positions/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updatePosition(id: number, data: Partial<{
    portfolio_id: number;
    asset_type: string;
    ticker: string;
    name: string;
    isin: string;
    quantity: number;
    currency: string;
  }>): Promise<any> {
    return request<any>(`/api/positions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deletePosition(id: number): Promise<any> {
    return request<any>(`/api/positions/${id}`, {
      method: 'DELETE',
    });
  },

  // Import schemas and uploads
  async getImportFileSchemas(): Promise<any[]> {
    return request<any[]>('/api/import-file-schemas/');
  },

  async createImportFileSchema(data: {
    name: string;
    is_public: boolean;
    delimiter: string;
    decimal_separator: string;
    mappings: string;
    is_incomplete?: boolean;
  }): Promise<any> {
    return request<any>('/api/import-file-schemas/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteImportFileSchema(id: number): Promise<any> {
    return request<any>(`/api/import-file-schemas/${id}`, {
      method: 'DELETE',
    });
  },

  async detectImportFileSchema(headers: string[]): Promise<any> {
    return request<any>('/api/import-file-schemas/detect', {
      method: 'POST',
      body: JSON.stringify(headers),
    });
  },

  async getImportMetadata(): Promise<any> {
    return request<any>('/api/portfolios/import-metadata');
  },

  async importPositions(
    portfolioId: number,
    file: File,
    schemaId: number | null,
    customSchemaConfig: any | null
  ): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (schemaId !== null) {
      formData.append('schema_id', String(schemaId));
    }
    if (customSchemaConfig !== null) {
      formData.append('custom_schema_config', JSON.stringify(customSchemaConfig));
    }

    const token = localStorage.getItem('kapital_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`/api/portfolios/${portfolioId}/import`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = 'Failed to import file.';
      try {
        const errorData = await response.json();
        if (errorData?.detail) errorMsg = errorData.detail;
      } catch {}
      throw new Error(errorMsg);
    }

    return response.json();
  }
};
