/** Canonical types shared across the website. */

export type Listing = {
  marketcheck_id: string;
  vin: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  exterior_color: string | null;
  interior_color: string | null;
  drivetrain: string | null;
  price: number;
  msrp: number | null;
  days_on_lot: number;
  dealer_name: string;
  dealer_email: string | null;
  dealer_phone: string | null;
  dealer_city: string;
  dealer_state: string;
  dealer_zip: string;
  distance_miles: number;
  vdp_url: string | null;
  photo_url: string | null;
  in_transit: boolean;
  vehicle_status: string | null;
};

export type CarInfo = {
  make: string;
  model: string;
  trims: string[];
  colors: string[];
  zipcode: string;
  radius: string;
};

export type SearchData = {
  car_info: CarInfo;
  listings: Listing[];
  num_found: number;
  email: string;
};

export type Selections = {
  make: string;
  model: string;
  trims: string[];
  colors: string[];
  zipcode: string;
  radius: string;
  email: string;
};

export type ReviewStatus = "pending" | "approved" | "cancelled";

export type ReviewListItem = {
  id: string;
  kind: string;
  status: ReviewStatus;
  title: string;
  customer_email: string;
  created_at: string;
  updated_at: string;
};

export type ReviewEmailDraft = {
  to: string;
  subject: string;
  html_body: string;
  full_html: string;
};

export type InitialStrategyEmailPayload = {
  car_info: CarInfo;
  marketcheck_raw: unknown;
  listings: Listing[];
  num_found: number;
  email: ReviewEmailDraft;
};

export type ReviewDetail = {
  id: string;
  kind: string;
  status: ReviewStatus;
  title: string;
  customer_email: string;
  search_result_id: string | null;
  payload: InitialStrategyEmailPayload;
  result: Record<string, unknown> | null;
  actor: string | null;
  created_at: string;
  updated_at: string;
  acted_at: string | null;
};

export type ReviewApproveResult = {
  success: boolean;
  send_result: {
    success: boolean;
    dry_run: boolean;
    error: string | null;
    message_id: string | null;
  };
};
