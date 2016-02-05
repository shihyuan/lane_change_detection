import pandas as pd
import sys

class TrafficData(object):
    def __init__(self,df):
        self.df = df
        self.df_by_veh = self.df.groupby('veh_id')
        self.df_by_frame = self.df.groupby('frame_id')
        self.veh_ids = sorted(df.veh_id.unique())
        self.lane_ids = sorted(df.lane_id.unique())
        self.frame_ids = sorted(df.frame_id.unique())
        
        self.lane_id_max = max(self.lane_ids)
        self.lane_id_min = min(self.lane_ids)

        # Extract lane centers
        self._lane_centers = dict()
        df_lane_id_group = self.df.groupby('lane_id')
        for lane_id, lane_df in df_lane_id_group:
            self._lane_centers[lane_id] = lane_df.local_x.mean()
            # print "lane_id: %s mean local_x: %s median %s" %(lane_id,lane_df.local_x.mean(),lane_df.local_x.median())

        # Fill extra data if not done already
        if 'lane_change' not in df.columns.values:
            self.fill_lanechange_data()
        else:
            print "lane_change available."

        if 'spacing_back' not in df.columns.values:
            self.fill_rear_spacing_data()
        else:
            print "spacing_back available."

        if 'vel_delta_front' not in df.columns.values:
            self.fill_vel_delta_data()
        else:
            print "vel_delta_front available."

        if 'vel_x' not in df.columns.values:
            self.fill_vel_x_data()
        else:
            print "vel_x available."

        print "Columns are: %s" %(self.df.columns.values)

    def fill_lanechange_data(self):
        # Add columns to the df
        self.df['lane_change'] = pd.Series(False,index=self.df.index)
        self.df['from_lane'] = pd.Series(index=self.df.index)
        # Find lanechanges and write to df
        print "Filling lane_change and from_lane"
        num_of_veh = len(self.veh_ids)
        count = 0.0
        for veh_id in self.veh_ids:
            host_veh_df = self.get_veh_df(veh_id)
            # Check for lane change
            if host_veh_df.lane_id.unique().size > 1:
                lane_diff = host_veh_df.lane_id.diff()
                lane_change_frames = host_veh_df.loc[abs(lane_diff) > 0]
                for index, row in lane_change_frames.iterrows():
                    self.df.loc[index,'lane_change'] = True
                    self.df.loc[index,'from_lane'] = row.lane_id - lane_diff.loc[index]
            count = count + 1.0
            ratio = count/num_of_veh
            sys.stdout.write('\r')
            sys.stdout.write("[%-20s] %d%% %s/%s" % ('='*int(20*ratio), 100.0*ratio,int(count),num_of_veh))
            sys.stdout.flush()
        sys.stdout.write('\n')
        sys.stdout.flush()


    def fill_rear_spacing_data(self):
        # Use the 'spacing' of the rear vehicle as rear spacing.
        self.df['spacing_back'] = pd.Series(index=self.df.index)
        veh_front_groups = self.df.groupby('veh_front')
        num_of_veh_front = len(veh_front_groups.groups.keys())
        print "Filling spacing_back data."
        count = 0.0
        for front_veh_id, df_by_front in veh_front_groups:
            if front_veh_id > 0:
                front_veh_df = self.get_veh_df(front_veh_id)
                for rear_veh_id, rear_veh_df in df_by_front.groupby('veh_id'):
                    # For each vehicle that has the host car as front vehicle
                    frame_id_list = rear_veh_df.frame_id.values
                    # Set the spacing of the front vehicle on the corresponding frames
                    index = front_veh_df.index[front_veh_df.frame_id.isin(frame_id_list)]
                    self.df.loc[index,'spacing_back'] = rear_veh_df.spacing.values
                    # front_veh_df.loc[front_veh_df.frame_id.isin(frame_id_list),'spacing_rear'] = rear_veh_df.spacing.values
            count = count + 1.0
            ratio = count/num_of_veh_front
            sys.stdout.write('\r')
            sys.stdout.write("[%-20s] %d%% %s/%s" % ('='*int(20*ratio), 100.0*ratio,int(count),num_of_veh_front))
            sys.stdout.flush()
        sys.stdout.write('\n')
        sys.stdout.flush()

    def fill_vel_delta_data(self):
        self.df['vel_delta_front'] = pd.Series(index=self.df.index)
        veh_grouped = self.df.groupby('veh_id')
        print "Filling vel_delta_front"
        count = 0.0
        num_of_veh = len(self.veh_ids)
        for veh_id, veh_df in veh_grouped:    
            for front_veh_id, front_veh_df in veh_df.groupby('veh_front'):
                if front_veh_id > 0:
                    host_index = front_veh_df.index
                    frame_id_list = front_veh_df.frame_id.values
                    front_index = self.get_index_of_frames(frame_id_list,front_veh_id)
                    self.df.loc[host_index,'vel_delta_front'] = (self.df.loc[front_index,'veh_vel'].values - 
                        self.df.loc[host_index,'veh_vel'].values)
            count = count + 1.0
            ratio = count/num_of_veh
            sys.stdout.write('\r')
            sys.stdout.write("[%-20s] %d%% %s/%s" % ('='*int(20*ratio), 100.0*ratio,int(count),num_of_veh))
            sys.stdout.flush()
        sys.stdout.write('\n')
        sys.stdout.flush()

    def fill_vel_x_data(self):
        self.df['vel_x'] = pd.Series(index=self.df.index)
        veh_grouped = self.df.groupby('veh_id')
        print "Filling vel_x"
        num_of_veh = len(self.veh_ids)
        count = 0.0
        for veh_id, veh_df in veh_grouped:
            self.df.loc[veh_df.index,'vel_x'] = veh_df.local_x.diff()/0.01
            count = count + 1.0
            ratio = count/num_of_veh
            sys.stdout.write('\r')
            sys.stdout.write("[%-20s] %d%% %s/%s" % ('='*int(20*ratio), 100.0*ratio,int(count),num_of_veh))
            sys.stdout.flush()
        sys.stdout.write('\n')
        sys.stdout.flush()        

    def get_lane_center(self,lane_id):
        return self._lane_centers[lane_id]

    def get_veh_df_between(self,veh_id,frame_id_start=None, frame_id_end=None):
        veh_df = self.get_veh_df(veh_id)
        if frame_id_start == None:
            frame_id_start = min(veh_df.frame_id)
        
        if frame_id_end == None:
            frame_id_end = max(veh_df.frame_id)

        return veh_df.loc[(veh_df.frame_id >= frame_id_start) & (veh_df.frame_id <= frame_id_end)]

    def get_index_of_frames(self,frame_id_list,veh_id):
        veh_df = self.get_veh_df(veh_id)
        index_mask = veh_df.frame_id.isin(frame_id_list)
        return veh_df.index[index_mask]

    def get_frame_df(self,frame_id):
        return self.df_by_frame.get_group(frame_id)
    
    def get_veh_df(self,veh_id):
        return self.df_by_veh.get_group(veh_id)
    
    def get_veh_snapshot(self, frame_id, veh_id):
        frame_df = self.get_frame_df(frame_id)
        return frame_df.loc[frame_df.veh_id == veh_id].squeeze()
    
    def get_veh_ids_on_frame(self,frame_id):
        frame_df = self.get_frame_df(frame_id)
        return sorted(frame_df.veh_id.unique())
    
    def get_frame_ids_of_veh(self,veh_id):
        veh_df = self.get_veh_df(veh_id)
        return sorted(veh_df.frame_id.unique())
    
    def get_lane_id(self, frame_id, veh_id):
        veh_snapshot = self.get_veh_snapshot(frame_id, veh_id)
        return veh_snapshot.lane_id.values[0]
    
    def get_neighber_lanes(self,lane_id):
        lane_id_lower = lane_id - 1 if lane_id > self.lane_id_min else None
        lane_id_higher = lane_id + 1 if lane_id < self.lane_id_max else None
        return lane_id_lower, lane_id, lane_id_higher

    def get_lag_veh_id(self,frame_id,lane_id,local_y):
        frame_df = self.get_frame_df(frame_id)
        lane_df = frame_df.groupby('lane_id').get_group(lane_id)
        lane_df_lag = lane_df.loc[lane_df.local_y < local_y]
        return lane_df_lag.tail(1).veh_id.values[0]

    def get_lead_veh_id(self,frame_id,lane_id,local_y):
        frame_df = self.get_frame_df(frame_id)
        lane_df = frame_df.groupby('lane_id').get_group(lane_id)
        lane_df_lead = lane_df.loc[lane_df.local_y >= local_y]
        return lane_df_lead.head(1).veh_id.values[0]

    def get_gap_series(self,frame_start, frame_end, veh_id_front, veh_id_back):
        return self.get_diff_series(frame_start, frame_end, veh_id_front, veh_id_back,'local_y')

    def get_diff_series(self, frame_start, frame_end, veh_id_front, veh_id_back, column_name):
        df_front = self.get_veh_df_between(veh_id_front,frame_start,frame_end)
        df_back = self.get_veh_df_between(veh_id_back,frame_start,frame_end)
        df_back = df_back.set_index('frame_id')
        df_front = df_front.set_index('frame_id')
        return df_front[column_name].subtract(df_back[column_name])
