%%%% Updated on: (06/04/2020)
%%%% Vans allocations and charging during daytime and overnight with spare
%%%% capacity at sites as constraints
%%%% Journeys that exceed the EV mileages are done by Diesel vehicles and
%%%% EVs get assigned when there arent any diesel vehicle available to do
%%%% the journey

%% Directories
savedir1 = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\';
savedir2 = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\sumOfHH\'; %% charging output files
savedir4 = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\allCasesAllData\';
allCasesVerticalOutputdir = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\allCasesVerticalOutputAddedColumns\';

%% Files name
branch_idindex_file = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\branch_idindex_file_allCasesAllocCharging.mat';
branch_id_file = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\branch_id_file_allCasesAllocCharging.mat';
sortbranch_id_file = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\sortbranch_id_file_allCasesAllocCharging.mat';
path_name_ev = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\ev_vansNum_test.mat';
path_name_diesel = 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\diesel_vansNum_test.mat';

% inputs
initial_SoC = 1;
charger_rating = [3.3,6.3,9.9,45];

inputsMatrix = [41.4,41,55,60,82.5;0.563,0.717,0.738,0.604,0.664;74.1,57.17,74.56,99.4,124.3;583,944,846,1932.5,846; 52,72,72,107,129];

matrixSize = size(inputsMatrix,2);

ASC_matrix = readtable('Store_ASC.csv'); % matrix containing or table containing supply capacity at stores
Power_factor = 0.95;
year_chosen = 2019;
refrigeratorPowerConsumption = 0.5;
%File containing journey data
journeysall = readtable('revised_mileages.csv'); 
journeysall = journeysall(year(journeysall.Start_Date_of_Route)==year_chosen,:);

journeysall = sortrows(journeysall,'Branch_ID');
branch_id = unique(journeysall.Branch_ID);
sizeOfBranch_id = size(branch_id,1);

%Calculating energy consumed by refrigeration
journeysall.Planned_total_Route_time = journeysall.End_Time_of_Route - journeysall.Start_Time_of_Route;
journeyTime = datevec(journeysall.Planned_total_Route_time); 
journeyTime = (hours(journeyTime(:,4)) + minutes(journeyTime(:,5))); 
energyUsedByRefrige = refrigeratorPowerConsumption .* hours(journeyTime); 

energyUsedByRefrige = array2table(energyUsedByRefrige);
journeysall = [journeysall,energyUsedByRefrige];
   
 simjAll = [];

 %Calculates simultaneous journeys for each store
  for b=1:sizeOfBranch_id 

            journeystemp = journeysall(journeysall.Branch_ID == branch_id(b),:);

            
            newJourneysall = sortrows(journeystemp,{'Branch_ID', 'Start_Date_of_Route', 'Start_Time_of_Route'});
            
            newJourneysall.Start_Date_of_Route.Format = 'dd/MM/yyyy HH:mm:ss';
            newJourneysall.Start_Time_of_Route = datenum(newJourneysall.Start_Date_of_Route) + datenum(newJourneysall.Start_Time_of_Route) - floor(datenum(newJourneysall.Start_Time_of_Route));
            newJourneysall.Start_Time_of_Route  = datetime(newJourneysall.Start_Time_of_Route ,'ConvertFrom','datenum');
            newJourneysall.End_Time_of_Route = datenum(newJourneysall.Start_Date_of_Route) + datenum(newJourneysall.End_Time_of_Route) - floor(datenum(newJourneysall.End_Time_of_Route));
            newJourneysall.End_Time_of_Route  = datetime(newJourneysall.End_Time_of_Route ,'ConvertFrom','datenum');
            
            string_start_timesj = string(newJourneysall.Start_Time_of_Route);
            string_end_timesj = string(newJourneysall.End_Time_of_Route);
            
            start_ttsj = datevec(string_start_timesj);
            stH = 60*(start_ttsj(:,4));
            stM = start_ttsj(:,5);
            startMinute = stH +stM;
            
            end_ttsj = datevec(string_end_timesj);
            endH = 60*(end_ttsj(:,4));
            endM = end_ttsj(:,5);
            endMinute = endH +endM;
            
            startMinuteTable = table((startMinute.*ones(size(startMinute,1),1)), 'VariableNames', {'startMinute'});
            endMinuteTable = table((endMinute.*ones(size(endMinute,1),1)), 'VariableNames', {'endMinute'});
            
            newJourneysall = [newJourneysall,startMinuteTable,endMinuteTable];
            numjourneys=size(newJourneysall,1);
            
            simj = [];
                       
            datesSimJourn_ = datenum(string(newJourneysall.Start_Date_of_Route),'dd/mm/yyyy');
            sortDatesSimJourn_ = sort(datesSimJourn_);
            datesindexSimJourn = [1,find(diff(sortDatesSimJourn_))'+1];
            datesindexSimJourn;
            datesSimJourn = sortDatesSimJourn_(datesindexSimJourn);
            date_sizeSimJourn = size(datesSimJourn,1);
            dates_indexSimJourn = [datesindexSimJourn,numjourneys+1];
            
            for day=1:date_sizeSimJourn 
                
                dates_indexSimJourn(day); dates_indexSimJourn(day+1);
                journeysday = newJourneysall(dates_indexSimJourn(day):dates_indexSimJourn(day+1)-1,:);
                
                minst = min(journeysday.startMinute);
                maxet = max(journeysday.endMinute);
                numj = size(journeysday,1);
                
                journs = zeros(numj,maxet-minst+1); %% matrix of journeys
                
                for f=1:numj
                    
                  
                    journs(f,[(journeysday.startMinute(f)-minst+1):(journeysday.endMinute(f)-minst+1)])=ones(1,journeysday.endMinute(f)-journeysday.startMinute(f)+1);
                    
                end 
                
                if numj>1
                    
                    maxSimNum = max(sum(journs));
                    
                else
                    
                    maxSimNum = 1;
                    
                end
                
                simj = [simj;datesSimJourn(day),maxSimNum];
                
            end
                       
            totalSimJourn = max(simj(:,2));
            simjAll = [simjAll;branch_id(b),totalSimJourn];
            simjAll1 = array2table(simjAll);
            simjAll1.Properties.VariableNames = {'Branch_id', 'simultaneousJourn'};
            writetable(simjAll1,[savedir1 'Simultaneous_journey.csv']);
  end     
  
  %Loop through each vehicle type
  for jj=1:matrixSize 
    
    eachCase = inputsMatrix(:,jj);
    pack_capacity = eachCase(1);
    start_energy = initial_SoC*pack_capacity;
    energy_per_mile = eachCase(2);
    this_max_mpr = eachCase(3);
    this_max_kgs = eachCase(4);
    max_crates = eachCase(5);
    
    for cr=1:numel(charger_rating)  %Loop through each charger type
        
        HH_energy_transfer = charger_rating(cr)/2;
        max_mpr = this_max_mpr;
        
        journeysall.equivalMileage = journeysall.energyUsedByRefrige/energy_per_mile;
        journeysall.newJourneyMileage = journeysall.Planned_total_Mileage +  journeysall.equivalMileage;
        numberOfJourneysall = size(journeysall,1);
        
  
        
        a_test=[];
        a_test_d=[];
        
        numvans = 500;
        numvans_d = 500;
        
        for b=1:sizeOfBranch_id %Loop through each store
             minnumvans_d = 0;
            minnumvans = 0;
        
            %Load in data for store loads 
        thispc_ = readtable(['Store_Loads_',num2str(branch_id(b)),'.xlsx']); 
        thispc = sortrows(thispc_,{'Date'});
        datespc = thispc.Date;
        dates_pc = datenum(datespc); 
        datesTable = array2table(dates_pc);
        thispcNew = [thispc,datesTable];
        datepc = thispcNew.dates_pc;
        sortThispcNew = sort(datepc);
        dd_size = sortThispcNew(end) - sortThispcNew(1) +1; 
        thispcNeww = movevars(thispcNew,'dates_pc','Before','Date');
        %Subtracting the ASC (kVa) from the Store Loads 
        thispcNeww.PowerCon = ASC_matrix.ASC(ASC_matrix.Branch_id == branch_id(b)) - (thispcNeww.kWh ./ Power_factor);
        thispcNeww = movevars(thispcNeww,'PowerCon','Before','kWh'); 
        thispcNeww = removevars(thispcNeww,{'Date','Store'}); 
        thisMat = thispcNeww;
        
     
         journeystemp = journeysall(journeysall.Branch_ID == branch_id(b),:);
            T1=table(zeros(size(journeystemp,1),1), 'VariableNames', {'Energy_Required'});
            T2=table(zeros(size(journeystemp,1),1), 'VariableNames', {'Energy_Needed'});
            journeys = [journeystemp, T1,T2];
            clear journeystemp;
           
            journeys(:,(end-1)) = array2table(journeys.newJourneyMileage*energy_per_mile);
            journeys(:,end) = array2table(journeys.Energy_Required);
            
            T3=table(zeros(size(journeys,1),1), 'VariableNames', {'vannumber_ev_'});
            T4=table(zeros(size(journeys,1),1), 'VariableNames', {'vannumber_d_'});
            journeys = [journeys, T3,T4];
         
             journeys = sortrows(journeys,{'Branch_ID', 'Start_Date_of_Route', 'Start_Time_of_Route'});
            
            journeys.Start_Date_of_Route.Format = 'dd/MM/yyyy HH:mm:ss';
            journeys.Start_Time_of_Route = datenum(journeys.Start_Date_of_Route) + datenum(journeys.Start_Time_of_Route) - floor(datenum(journeys.Start_Time_of_Route));
            journeys.Start_Time_of_Route  = datetime(journeys.Start_Time_of_Route ,'ConvertFrom','datenum');
            journeys.End_Time_of_Route = datenum(journeys.Start_Date_of_Route) + datenum(journeys.End_Time_of_Route) - floor(datenum(journeys.End_Time_of_Route));
            journeys.End_Time_of_Route  = datetime(journeys.End_Time_of_Route ,'ConvertFrom','datenum');
      
             sortDates_ = sort(datenum(journeys.Start_Date_of_Route));
            
            d1 = sortDates_(1);
            d2 = sortDates_(end);
            d = d1:d2;
            dates_new = d'; %Containing all days within the date range
            
            datesindex_new = [1,find(diff(dates_new))'+1];
         
            numberofDays_new = size(datesindex_new,2);
            
            date_size = sortDates_(end)-sortDates_(1)+1;
             numberOfRows = 48*date_size;
           
            hh = mod([0:(numberOfRows-1)]',48);
            
            datevector=[];
            
            %Creating matrix with HH periods for the date range
            for j=d(1):d(end)
                
                datevector = [datevector; j*ones(48,1)];
                
            end
            
            index1 = find(thisMat{:,1}==sortDates_(1));
            index2 = find(thisMat{:,1}==sortDates_(end));
            idx1 = index1(1);
            idx2 = index2(end);
            idxx = (idx1:idx2)';
            extracted1 = thisMat{idxx,:};
            extracted = extracted1(:,(3)); % Column containing the remaining capacity at sites (kVa)
            
            van_energy_profile = zeros(date_size*48,((numvans*2) + 2));
            van_energy_profile(:,1) = datevector;
            van_energy_profile(:,2) = hh;
            van_energy_profile(1,3:2:(end-1)) = start_energy*ones(1,numvans);
            van_energy_profile(:,4:2:end) = HH_energy_transfer*ones(date_size*48,numvans);
            van_energy_profile = [van_energy_profile,extracted]; % adding remaning capacity column at van energy matrix
            
            dieselMpr = journeys.newJourneyMileage;
            kgs = journeys.Loaded_Kgs;
            crates = journeys.Loaded_Total_Crates;

            journeysE = journeys(dieselMpr < this_max_mpr & kgs <= (this_max_kgs+1) & crates <= (max_crates+1),:);
            journeysEE = journeys(dieselMpr < this_max_mpr & kgs > (this_max_kgs+1) | crates > (max_crates+1),:);
            journeysDD = journeys(dieselMpr > this_max_mpr,:);
            journeysD = [journeysDD;journeysEE];
            
            if isempty(journeysD) 
                
                numberOfJourneysD =0;
                minnumvans_d=0;
                
            else 
                
                numberOfJourneysD = size(journeysD,1);
                matrixOfVans_d = ones(numberOfRows, numvans_d);
                
                journeysD = sortrows(journeysD, {'Start_Date_of_Route', 'Start_Time_of_Route'});
                string_start_time = journeysD.Start_Time_of_Route;
                string_time_st = string(string_start_time);
                
                string_end_time = journeysD.End_Time_of_Route;
                string_time_end = string(string_end_time);
                for jD=1:numberOfJourneysD 
                    
                    start_tt = datevec(string_time_st(jD));
                    change_timeST = round(2*(start_tt(4) + (start_tt(5))/60));
                    timeST = sortrows(change_timeST);
                    dateSTindex = find(dates_new==datenum(journeysD.Start_Date_of_Route(jD)))-1;
                    rownumST = dateSTindex*48+timeST+1;
                    
                    end_tt = datevec(string_time_end(jD));
                    change_timeEND = round(2*(end_tt(4) + (end_tt(5))/60));
                    timeEND = change_timeEND;
                    rownumEND = dateSTindex*48+timeEND+1;
                    
                    vannum_d=find(matrixOfVans_d(rownumST,:),1);
                    matrixOfVans_d(rownumST:rownumEND,vannum_d)=zeros(rownumEND-rownumST+1,1);
                    
                    if vannum_d > minnumvans_d
                        
                        minnumvans_d = vannum_d;
                        
                    end
                    
                    journeysD(jD, end) = {vannum_d};
                    
                end  
                
            end 

            numberOfJourneysE = size(journeysE,1);            
            matrixOfVans = ones(numberOfRows, numvans);
            
            journeysE = sortrows(journeysE, {'Start_Date_of_Route', 'Start_Time_of_Route'});
            string_start_time = journeysE.Start_Time_of_Route;
            string_time_st = string(string_start_time);
            
            string_end_time = journeysE.End_Time_of_Route;
            string_time_end = string(string_end_time);
            
            rownumST = 1;
            endtimevector  = [];
            
            
            minnumvans = max((simjAll1{b,2} - minnumvans_d),0);
            
            for j=1:numberOfJourneysE
                
                rownumSTold = rownumST;
                
                start_tt = datevec(string_time_st(j));
                change_timeST = round(2*(start_tt(4) + (start_tt(5))/60));
                timeST = change_timeST;
                dateSTindex = find(dates_new==datenum(journeysE.Start_Date_of_Route(j)))-1;
                rownumST = dateSTindex*48+timeST+1;
                
                if rownumST > rownumSTold
                    
                    for rownums=rownumSTold:(rownumST-1)                        
                       
                        currentload=0;
                        
                        for vs=1:numvans
                            
                            van_energy_profile(rownums,2*vs+2) = min(van_energy_profile(rownums,2*vs+2), van_energy_profile(rownums,end)-currentload); 
                            van_energy_profile(rownums+1,2*vs+1) = min(pack_capacity, van_energy_profile(rownums,2*vs+1)+van_energy_profile(rownums,2*vs+2)); 
                            van_energy_profile(rownums,2*vs+2) = van_energy_profile(rownums+1,2*vs+1)- van_energy_profile(rownums,2*vs+1); 
                            currentload=currentload+(max(van_energy_profile(rownums,2*vs+2),0)*2/Power_factor); 
                            
                        end                        
                      
                    end
                    
                end
                
                end_tt = datevec(string_time_end(j));
                change_timeEND = round(2*(end_tt(4) + (end_tt(5))/60));
                timeEND = change_timeEND;
                rownumEND = dateSTindex*48+timeEND+1;
                vantempnum = find(matrixOfVans(rownumST,:));
                
                sizetemp = length(vantempnum);
                
                if(sizetemp==0)
                    
                    warning('not enough vans ...!!! ');
                    
                    break
                    
                end
                
                mytest=0;
                idx=0;
                 while(mytest==0)
                    
                    idx=idx+1;
                    vannum = vantempnum(idx);
                    
                    if vannum>minnumvans | (min(pack_capacity, van_energy_profile(rownumST, 2*vannum+1))>(journeysE.newJourneyMileage(j)*energy_per_mile))
                        
                        mytest = 1;
                        
                    end
                    
                 end  
                
                  if vannum > minnumvans
                    
                    if minnumvans_d>0
                        
                        dvMatrix = matrixOfVans_d(rownumST:rownumEND,:);
                        dv = 1;
                        
                        while ((dv <= minnumvans_d) & (max(dvMatrix(:,dv)'~=ones(size(dvMatrix(:,dv)')))))
                            
                            max(dvMatrix(:,dv)'~=ones(size(dvMatrix(:,dv)',1)));
                            dv = dv+1;
                            
                        end
                        

                        
                        if dv > minnumvans_d
                            
                            matrixOfVans(rownumST:rownumEND,vannum)=zeros(rownumEND-rownumST+1,1);
                            
                            journeysE(j, end-1) = {vannum};
                            minnumvans = vannum;
                                                     
                            endtimevector(vannum) = rownumEND;
                            
                            van_energy_profile(rownumST:rownumEND,2+2*vannum)=-journeysE.newJourneyMileage(j)*energy_per_mile/(-rownumST+rownumEND+1)*ones(rownumEND-rownumST+1,1);
                            
                        else
                            
                            vannum_d = dv;
                            matrixOfVans_d(rownumST:rownumEND,vannum_d)=zeros(rownumEND-rownumST+1,1);
                          
                        journeysE(j, end) = {vannum_d};
                            
                        end
                        
                    else
                        
                        matrixOfVans(rownumST:rownumEND,vannum)=zeros(rownumEND-rownumST+1,1);
                   
                        journeysE(j, end-1) = {vannum};
                        minnumvans = vannum;
                       endtimevector(vannum) = rownumEND;
                        
                        van_energy_profile(rownumST:rownumEND,2+2*vannum)=-journeysE.newJourneyMileage(j)*energy_per_mile/(-rownumST+rownumEND+1)*ones(rownumEND-rownumST+1,1);
                        
                    end
                    
                else
                    
                    matrixOfVans(rownumST:rownumEND,vannum)=zeros(rownumEND-rownumST+1,1);
                    
                    journeysE(j, end-1) = {vannum};                    
        
                    van_energy_profile(rownumST:rownumEND,2+2*vannum)=-journeysE.newJourneyMileage(j)*energy_per_mile/(-rownumST+rownumEND+1)*ones(rownumEND-rownumST+1,1);
                    
                    endtimevector(vannum) = rownumEND;
                    
                end
                
            end
            
            for rownums=rownumST:size(van_energy_profile,1)                

                currentload=0;
                
                for vs=1:numvans 
                    
                    van_energy_profile(rownums,2*vs+2) = min(van_energy_profile(rownums,2*vs+2), van_energy_profile(rownums,end)-currentload); 
                    van_energy_profile(rownums+1,2*vs+1) = min(pack_capacity, van_energy_profile(rownums,2*vs+1)+van_energy_profile(rownums,2*vs+2)); 
                    van_energy_profile(rownums,2*vs+2) = van_energy_profile(rownums+1,2*vs+1)- van_energy_profile(rownums,2*vs+1); 
                    currentload=currentload+(max(van_energy_profile(rownums,2*vs+2),0)*2/Power_factor); 
                    
                end 
           end
            
            for rownums=rownumST:(48*date_size-1)
                
                van_energy_profile(rownums+1,3:2:(end-1)) = min(pack_capacity, van_energy_profile(rownums,3:2:(end-1))+van_energy_profile(rownums,4:2:end));
                
            end
            
            for rownums=1:(48*date_size-1)
                
                van_energy_profile(rownums,4:2:end) = van_energy_profile(rownums+1,3:2:(end-1))-van_energy_profile(rownums,3:2:(end-1));
                
            end
  
            van_energy_profile = van_energy_profile(van_energy_profile(:,1)>0,:);          
            
            temp=size(van_energy_profile,1);
            van_energy_profile(temp,4:2:end)=min(pack_capacity-van_energy_profile(temp,3:2:(end-1)), van_energy_profile(temp,4:2:end));

            vans_p = array2table(van_energy_profile);
            writetable(vans_p,[savedir1 num2str(branch_id(b)) '_vanEnergyProfileTable_' num2str(pack_capacity) '_' num2str(energy_per_mile) '_' num2str(charger_rating(cr)) '.csv'],'Delimiter',',');
   
            if isempty(journeysD)
                
                %% do nothing: No DV
                
            else
                
                while(nnz(matrixOfVans_d(:,minnumvans_d+1))<numberOfRows && minnumvans_d<numvans_d-1)
                    
                    minnumvans_d=minnumvans_d+1;
                    
                end
                
               
                
                a_test_d = [a_test_d;branch_id(b), minnumvans_d];
                a_test_d1 = array2table(a_test_d);
                a_test_d1.Properties.VariableNames = {'Branch_id', 'diesel_vansNumber'};
                writetable(a_test_d1,[savedir1 num2str(this_max_mpr) '_d_fleetSize_' num2str(pack_capacity) '_' num2str(energy_per_mile) '_' num2str(charger_rating(cr)) '.csv'],'Delimiter',',');
                
                save(path_name_diesel, 'minnumvans_d');               
  

            end
            
            while(nnz(matrixOfVans(:,minnumvans+1))<numberOfRows && minnumvans<numvans-1)
                
                minnumvans=minnumvans+1;
                
            end
            
            
            
            vep = van_energy_profile;
            N = minnumvans;
            X = [];
            
            if N > 0 
                
                for k=1:N
                    
                    X = [X;[vep(:,[1,2,2*k+1, 2*k+2]),k*ones(size(vep,1),1)]];
                    
                end
                
                Xsize = size(X,1);
                XX = [branch_id(b)*ones(size(X,1),1),X,charger_rating(cr)*ones(size(X,1),1)];
                XX_Table = array2table(XX);
                XX_Table.Properties.VariableNames = {'Branch_ID','numDates','HH','Pack_Capacity','HH_Energy_Transfer','EV_number','Charger_type'};
                
                all_filesVert = XX_Table; 
                dVert = datestr(all_filesVert.numDates, 'dd/mm/yyyy');
                Dates = cellstr(dVert);
                dVert_table = cell2table(Dates);
                new_all_filesVert = [dVert_table,all_filesVert];
                writetable(new_all_filesVert,[allCasesVerticalOutputdir 'new_allCasesVerticalOutputFile_' num2str(branch_id(b)) '_' num2str(pack_capacity) '_' num2str(charger_rating(cr)) '.csv'],'Delimiter',',');
                
            end        
            a_test=[a_test;branch_id(b), minnumvans];
            a_test1 = array2table(a_test);
            a_test1.Properties.VariableNames = {'Branch_id', 'ev_vansNumber'};
            writetable(a_test1,[savedir1 num2str(this_max_mpr) '_ev_fleetSize_' num2str(pack_capacity) '_' num2str(energy_per_mile) '_' num2str(charger_rating(cr)) '.csv'],'Delimiter',',');
            
            finalMatrix=[datevector,mod([0:(numberOfRows-1)]',48),minnumvans-sum((matrixOfVans(:, 1:minnumvans)),2), (matrixOfVans(:, 1:minnumvans))];
            
            chargertype = charger_rating(cr)*ones(size(journeysD,1),1);
            tableD = array2table(chargertype);
            new_journeysD = [journeysD,tableD];
            writetable(new_journeysD,[savedir1 num2str(this_max_mpr) '_newstoreD_' num2str(branch_id(b)) '_' num2str(pack_capacity) '_' num2str(energy_per_mile) '_' num2str(charger_rating(cr)) '.csv'],'Delimiter',',');
            
            chargerType = charger_rating(cr)*ones(size(journeysE,1),1);
            tableE = array2table(chargerType);
            new_journeysE = [journeysE,tableE];
            writetable(new_journeysE,[savedir1 num2str(this_max_mpr) '_newstoreE_' num2str(branch_id(b)) '_' num2str(pack_capacity) '_' num2str(energy_per_mile) '_' num2str(charger_rating(cr)) '.csv'],'Delimiter',','); %% saving data for EV
            
        end  
        
    end
  end


      


%% Save output files in folders
cd 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\'

% % %%-------------- EV80 ---------------------
copyfile *95.94_* ev80/.
copyfile *95.94_newstoreD_* ev80_storeD/.
copyfile *95.94_newstoreE_* ev80_storeE/.
% % %%-----------------------------------------------

%%-------------- Renault Master ZE ----------------
% copyfile *60.148_* masterZE/.
% copyfile *60.148_newstoreD_* masterZE_storeD/.
% copyfile *60.148_newstoreE_* masterZE_storeE/.
%%----------------------------------------------

% % %%-------------- eVito -------------------------------
% % copyfile *74.1_* eVito/.
% % copyfile *74.1_newstoreD_* eVito_storeD/.
% % copyfile *74.1_newstoreE_* eVito_storeE/.
% % %%-----------------------------------------------------
% % 
% % %%-------------- eSprinter Low Range -------------------------------
% % copyfile *57.17_* eSprinterLowRange/.
% % copyfile *57.17_newstoreD_* eSprinterLowRange_storeD/.
% % copyfile *57.17_newstoreE_* eSprinterLowRange_storeE/.
% % %%-----------------------------------------------------
% % 
% % %%-------------- eSprinter Hi Range -------------------------------
% % copyfile *74.561_* eSprinterHiRange/.
% % copyfile *74.561_newstoreD_* eSprinterHiRange_storeD/.
% % copyfile *74.561_newstoreE_* eSprinterHiRange_storeE/.
% % %%-----------------------------------------------------
% % 
% % %%-------------- eSprinter Hi 3.9T -------------------------------
% % copyfile *74.56_* eSprinterHi39TRange/.
% % copyfile *74.56_newstoreD_* eSprinterHi39TRange_storeD/.
% % copyfile *74.56_newstoreE_* eSprinterHi39TRange_storeE/.
% % %%-----------------------------------------------------
% % 
% % %%--------------- T4 --------------------------------
% % copyfile *99.4_* T4/.
% % copyfile *99.4_newstoreD_* T4_storeD/.
% % copyfile *99.4_newstoreE_* T4_storeE/.
% % %%--------------------------------------------

% % %%------------------ copy fleetSize files ------------------
% % copyfile *95.94_ev_fleetSize* evFleetEV80/.
% % copyfile *95.94_d_fleetSize* dieselFleetEV80/.
% copyfile *60.148_ev_fleetSize* evFleetRenauldMasterZE/.
% copyfile *60.148_d_fleetSize* dieselFleetRenauldMasterZE/.
% % copyfile *74.1_ev_fleetSize* evFleeteVito/.
% % copyfile *74.1_d_fleetSize* dieselFleeteVito/.
% % copyfile *57.17_ev_fleetSize* evFleeteSprinterLowRange/.
% % copyfile *57.17_d_fleetSize* dieselFleeteSprinterLowRange/.
% % copyfile *74.561_ev_fleetSize* evFleeteSprinterHiRange/.
% % copyfile *74.561_d_fleetSize* dieselFleeteSprinterHiRange/.
% % copyfile *74.56_ev_fleetSize* evFleeteSprinterHi39TRange/.
% % copyfile *74.56_d_fleetSize* dieselFleeteSprinterHi39TRange/.
% % copyfile *99.4_ev_fleetSize* evFleetT4/.
% % copyfile *99.4_d_fleetSize* dieselFleetT4/.
% % %%----------------------------------------------------

%% Save charging output files (vertical concatenation)
cd 'C:\Users\FPSDashboard\OneDrive - Flexible Power Systems Ltd\JA_Models&Scripts\allCasesAllocCharging\allCasesVerticalOutputAddedColumns\';
copyfile *new_allCasesVerticalOutputFile* allCasesChargingVerticalOutputs/.
