%% Updated on (07/09/20)
%%% Script that allocates vehicle to journeys with charging options both at day and
%%% night

%% Directories
savedir1 = 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\';
allCasesVerticalOutputdir = 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\allCasesVerticalOutputAddedColumns\';

%% (.mat) files name
branch_idindex_file = 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\branch_idindex_file_allCasesAllocCharging.mat';
branch_id_file = 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\branch_id_file_allCasesAllocCharging.mat';
sortbranch_id_file = 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\sortbranch_id_file_allCasesAllocCharging.mat';
path_name_ev = 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\ev_vansNum_test.mat';
path_name_diesel = 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\diesel_vansNum_test.mat';

%% inputs
initial_SoC = 1;
charger_rating = [22];%[3.3,6.3,9.9,11,45];

journey_safety_margin = 0;
inputsMatrix = [75;0.46;164;1000; 80];
refrigeratorPowerConsumption = 0.5;
year_chosen = 2020;%then 2020
matrixSize = size(inputsMatrix,2);

tic

 data = readtable('select_journey_data.csv');
    journeysall = sortrows(data,'Branch_ID');
    journeysall = journeysall(year(journeysall.Start_Date_of_Route)==year_chosen,:);

    branch_id = unique(journeysall.Branch_ID);
       sortbranch_id = journeysall.Branch_ID;
        unique_branch_idindex = [1,find(diff(sortbranch_id))'+1];
        sizeOfBranch_id = size(branch_id,1);

%Calculating energy consumed by refrigeration
journeysall.Planned_total_Route_time = journeysall.End_Time_of_Route - journeysall.Start_Time_of_Route;
journeyTime = datevec(journeysall.Planned_total_Route_time); 
journeyTime = (hours(journeyTime(:,4)) + minutes(journeyTime(:,5))); 
energyUsedByRefrige = refrigeratorPowerConsumption .* hours(journeyTime); 

energyUsedByRefrige = array2table(energyUsedByRefrige);
journeysall = [journeysall,energyUsedByRefrige];
   


simjAll = [];

       for b=1:sizeOfBranch_id 
            
            minnumvans_d = 0;
            minnumvans = 0;
            simj = [];
            

             numberOfJourneysall = size(journeysall,1);
            branch_idindex = [unique_branch_idindex,numberOfJourneysall+1];
            journeystemp = journeysall(journeysall.Branch_ID == branch_id(b),:);
            newJourneysall = sortrows(journeystemp,{'Branch_ID', 'Start_Date_of_Route', 'Start_Time_of_Route'});
            
            newJourneysall.Start_Date_of_Route.Format = 'dd/MM/yyyy HH:mm:ss';
            newJourneysall.Start_Time_of_Route = datenum(newJourneysall.Start_Date_of_Route) + datenum(newJourneysall.Start_Time_of_Route) - floor(datenum(newJourneysall.Start_Time_of_Route));
            newJourneysall.Start_Time_of_Route  = datetime(newJourneysall.Start_Time_of_Route ,'ConvertFrom','datenum');
            newJourneysall.End_Time_of_Route = datenum(newJourneysall.Start_Date_of_Route) + datenum(newJourneysall.End_Time_of_Route) - floor(datenum(newJourneysall.End_Time_of_Route));
            newJourneysall.End_Time_of_Route  = datetime(newJourneysall.End_Time_of_Route ,'ConvertFrom','datenum');
            
            string_start_timesj = string(newJourneysall.Start_Time_of_Route);
            string_end_timesj = string(newJourneysall.End_Time_of_Route);
            
            start_ttsj = datevec(cellstr(string_start_timesj)); %ST added cellstr()
            stH = 60*(start_ttsj(:,4));
            stM = start_ttsj(:,5);
            startMinute = stH +stM;
            
            end_ttsj = datevec(cellstr(string_end_timesj));%ST added cellstr()
            endH = 60*(end_ttsj(:,4));
            endM = end_ttsj(:,5);
            endMinute = endH +endM;
            
            startMinuteTable = table((startMinute.*ones(size(startMinute,1),1)), 'VariableNames', {'startMinute'});
            endMinuteTable = table((endMinute.*ones(size(endMinute,1),1)), 'VariableNames', {'endMinute'});
            
            newJourneysall = [newJourneysall,startMinuteTable,endMinuteTable];
            numjourneys=size(newJourneysall,1);
            
            %datesSimJourn_ = datenum(string(newJourneysall.Start_Date_of_Route),'dd/mm/yyyy');
            datesSimJourn_ = datenum(cellstr(newJourneysall.Start_Date_of_Route),'dd/mm/yyyy');
            sortDatesSimJourn_ = sort(datesSimJourn_);
            datesindexSimJourn = [1,find(diff(sortDatesSimJourn_))'+1];
            datesSimJourn = sortDatesSimJourn_(datesindexSimJourn);
            date_sizeSimJourn = size(datesSimJourn,1);
            dates_indexSimJourn = [datesindexSimJourn,numjourneys+1];
            
            for day= 1:date_sizeSimJourn
                
                journeysday = newJourneysall(dates_indexSimJourn(day):dates_indexSimJourn(day+1)-1,:);
                
                minst = min(journeysday.startMinute);
                maxet = max(journeysday.endMinute);
                numj = size(journeysday,1);
                
                journs = zeros(numj,maxet-minst+1);
                
                for f= 1:numj
                    
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

       end
% % %     

%        
       
   for jj= 1:matrixSize

    eachCase = inputsMatrix(:,jj);
    pack_capacity = eachCase(1);
    start_energy = initial_SoC*pack_capacity;
    energy_per_mile = eachCase(2);
    this_max_mpr = eachCase(3);
    this_max_kgs = eachCase(4);
    max_crates = eachCase(5);
    
    for cr= numel(charger_rating)
        
        HH_energy_transfer = charger_rating(cr)/2;
        max_mpr = this_max_mpr;
        journeysall.equivalMileage = journeysall.energyUsedByRefrige/energy_per_mile;
        journeysall.newJourneyMileage = journeysall.Planned_total_Mileage +  journeysall.equivalMileage;
        numberOfJourneysall = size(journeysall,1);
        

        a_test=[];
        a_test_d=[];
        
        numvans = 500;
        numvans_d = 500;
        
       for b=1:sizeOfBranch_id
           
           minnumvans_d = 0;
            minnumvans = 0;
           
           journeystemp = journeysall(journeysall.Branch_ID == branch_id(b),:);
           T1=table(zeros(size(journeystemp,1),1), 'VariableNames', {'Energy_Required'});
           T2=table(zeros(size(journeystemp,1),1), 'VariableNames', {'Energy_Needed'});
           journeys = [journeystemp, T1,T2];
           
           journeys(:,(end-1)) = array2table(journeys.newJourneyMileage*energy_per_mile);
            journeys(:,end) = array2table(journeys.Energy_Required*(1+journey_safety_margin));
            
            T3=table(zeros(size(journeys,1),1), 'VariableNames', {'vannumber_ev_'});
            T4=table(zeros(size(journeys,1),1), 'VariableNames', {'vannumber_d_'});
            journeys = [journeys, T3,T4];
            
            %clear newJourneysall 
             %journeys;
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
            d = d';
            %%d = datenum(string(d,'dd/mm/yyyy'));
            datesindex = [1,find(diff(sortDates_))'+1];
            datesindex_new = [1,find(diff(d))'+1];
            dates = sortDates_(datesindex);
            dates_new = d;
            numberOfDays = size(datesindex,2);
            numberofDays_new = size(datesindex_new,2);
            
            date_size = sortDates_(end)-sortDates_(1)+1;
            
                        
            numberOfRows = 48*date_size;
            hh = mod([0:(numberOfRows-1)]',48);
             datevector=[];
            
            for j=d(1):d(end)
                
                datevector = [datevector; j*ones(48,1)];
                
            end
            
            van_energy_profile = zeros(date_size*48,((numvans*2) + 2));
            van_energy_profile(:,1) = datevector;
            van_energy_profile(:,2) = hh;
            van_energy_profile(1,3:2:(end-1)) = start_energy*ones(1,numvans);
            van_energy_profile(:,4:2:end) = HH_energy_transfer*ones(date_size*48,numvans);
            
            dieselMpr = journeys.newJourneyMileage;
            kgs = journeys.Loaded_Kgs;
            crates = journeys.Loaded_Total_Crates;
           
            
            journeysE = journeys(dieselMpr < this_max_mpr & kgs <= (this_max_kgs+1) & crates <= (max_crates+1),:);
            journeysEE = journeys(dieselMpr < this_max_mpr & kgs > (this_max_kgs+1) | crates > (max_crates+1),:);
            journeysDD = journeys(dieselMpr > this_max_mpr,:);
            journeysD = [journeysDD;journeysEE];
            
            
             if isempty(journeysD)
                
                numberOfJourneysD = 0;
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
                    
                    start_tt = datevec(cellstr(string_time_st(jD))); %ST cellstr
                    change_timeST = round(2*(start_tt(4) + (start_tt(5))/60));
                    timeST = sortrows(change_timeST);
                    dateSTindex = find(dates_new==datenum(journeysD.Start_Date_of_Route(jD)))-1;
                    rownumST = dateSTindex*48+timeST+1
                    
                    end_tt = datevec(cellstr(string_time_end(jD))); %ST cellstr
                    change_timeEND = round(2*(end_tt(4) + (end_tt(5))/60));
                    timeEND = change_timeEND;
                    rownumEND = dateSTindex*48+timeEND+1
                    
                    vannum_d = find(matrixOfVans_d(rownumST,:),1);
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
            
            simjAll1{b,2} - minnumvans_d;
            minnumvans = max((simjAll1{b,2} - minnumvans_d),0);
%             
                   for j=1:numberOfJourneysE
                
                        rownumSTold = rownumST;
                        start_tt = datevec(cellstr(string_time_st(j)));
                        change_timeST = round(2*(start_tt(4) + (start_tt(5))/60));
                    timeST = change_timeST;
                    dateSTindex = find(dates_new==datenum(journeysE.Start_Date_of_Route(j)))-1;
                    rownumST = dateSTindex*48+timeST+1;
                
                if rownumST > rownumSTold
                    
                    for rownums=rownumSTold:(rownumST-1)
                        
                        van_energy_profile(rownums+1,3:2:(end-1)) = min(pack_capacity, van_energy_profile(rownums,3:2:(end-1))+van_energy_profile(rownums,4:2:end));
                        
                    end
                    
                end
                
                end_tt = datevec(cellstr(string_time_end(j)));
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
%                     minnumvans = vannum;
                 else
                    
                    matrixOfVans(rownumST:rownumEND,vannum)=zeros(rownumEND-rownumST+1,1);
                    
                    journeysE(j, end-1) = {vannum};
                    %%minnumvans = vannum;
                    
                    van_energy_profile(rownumST:rownumEND,2+2*vannum)=-journeysE.newJourneyMileage(j)*energy_per_mile/(-rownumST+rownumEND+1)*ones(rownumEND-rownumST+1,1);
                    
                    endtimevector(vannum) = rownumEND;   
                end
                
                   end
            
            for rownums=rownumST:(48*date_size-1)
                
                van_energy_profile(rownums+1,3:2:(end-1)) = min(pack_capacity, van_energy_profile(rownums,3:2:(end-1))+van_energy_profile(rownums,4:2:end));
                
            end
            
            for rownums=1:(48*date_size-1)
                
                van_energy_profile(rownums,4:2:end) = van_energy_profile(rownums+1,3:2:(end-1))-van_energy_profile(rownums,3:2:(end-1));
                
            end
            
            van_energy_profile(:,4:2:end)=min(pack_capacity-van_energy_profile(:,3:2:(end-1)), van_energy_profile(:,4:2:end));
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
                
%                 finalMatrix_d=[datevector,mod([0:(numberOfRows-1)]',48),minnumvans_d-sum((matrixOfVans_d(:, 1:minnumvans_d)),2), (matrixOfVans_d(:, 1:minnumvans_d))];
                
            end
            
             while(nnz(matrixOfVans(:,minnumvans+1))<numberOfRows && minnumvans<numvans-1)
                
                minnumvans=minnumvans+1;
                
            end
            
            vep = van_energy_profile;
            N = minnumvans;
            X = [];
            
            if N > 0
                
                for k=1:N
                    
                    %[vep(:,[1,2,2*k+1, 2*k+2]),k*ones(size(vep,1),1)];
                    
                    X = [X;[vep(:,[1,2,2*k+1, 2*k+2]),k*ones(size(vep,1),1)]];
                    
                end
                
                Xsize = size(X,1);
                XX = [branch_id(b)*ones(size(X,1),1),X,charger_rating(cr)*ones(size(X,1),1)];
                XX_Table = array2table(XX);
                XX_Table.Properties.VariableNames = {'Branch_ID','numDates','HH','Pack_Capacity','HH_Energy_Transfer','EV_number','Charger_type'};
                
%                 writetable(XX_Table,[allCasesVerticalOutputdir 'allCasesVerticalOutputFile_' num2str(branch_id(b)) '_' num2str(pack_capacity) '_' num2str(charger_rating(cr)) '.csv'],'Delimiter',',');
                
                all_filesVert = XX_Table; % readtable([allCasesVerticalOutputdir, 'allCasesVerticalOutputFile_' num2str(branch_id(b)) '_' num2str(pack_capacity) '_' num2str(charger_rating(cr)) '.csv']);
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
            writetable(new_journeysE,[savedir1 num2str(this_max_mpr) '_newstoreE_' num2str(branch_id(b)) '_' num2str(pack_capacity) '_' num2str(energy_per_mile) '_' num2str(charger_rating(cr)) '.csv'],'Delimiter',',');
            
        end
        
       end
    
    end     
%   
  %% Save output files in folders
cd 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\'

%%-------------- EV80 ---------------------
% copyfile *95.94_* ev80/.
% copyfile *95.94_newstoreD_* ev80_storeD/.
% copyfile *95.94_newstoreE_* ev80_storeE/.
%%-----------------------------------------------
% 
%%-------------- Renault Master ZE ----------------
% copyfile *60.148_* masterZE/.
% copyfile *60.148_newstoreD_* masterZE_storeD/.
% copyfile *60.148_newstoreE_* masterZE_storeE/.
%%----------------------------------------------

% %%-------------- eVito -------------------------------
% copyfile *74.1_* eVito/.
% copyfile *74.1_newstoreD_* eVito_storeD/.
% copyfile *74.1_newstoreE_* eVito_storeE/.
% %%-----------------------------------------------------
% 
%%-------------- eSprinter Low Range -------------------------------
% copyfile *57.17_* eSprinterLowRange/.
% copyfile *57.17_newstoreD_* eSprinterLowRange_storeD/.
% copyfile *57.17_newstoreE_* eSprinterLowRange_storeE/.
%%-----------------------------------------------------

% %%-------------- eSprinter Hi Range -------------------------------
% copyfile *74.561_* eSprinterHiRange/.
% copyfile *74.561_newstoreD_* eSprinterHiRange_storeD/.
% copyfile *74.561_newstoreE_* eSprinterHiRange_storeE/.
% %%-----------------------------------------------------

% %%-------------- eSprinter Hi 3.9T -------------------------------
%copyfile *74.56_* eSprinterHi39TRange/.
%copyfile *74.56_newstoreD_* eSprinterHi39TRange_storeD/.
%copyfile *74.56_newstoreE_* eSprinterHi39TRange_storeE/.
% %%-----------------------------------------------------
% 
% %%--------------- T4 --------------------------------
% copyfile *99.4_* T4/.
% copyfile *99.4_newstoreD_* T4_storeD/.
% copyfile *99.4_newstoreE_* T4_storeE/.
% %%--------------------------------------------

%%--------------- Future --------------------------------
% copyfile *124.3_* T4/.
% copyfile *124.3_newstoreD_* T4_storeD/.
% copyfile *124.3_newstoreE_* T4_storeE/.
%%--------------------------------------------

%--------------- Vivaro --------------------------------
copyfile *164_* Vivaro/.
copyfile *164_newstoreD_* Vivaro_storeD/.
copyfile *164_newstoreE_* Vivaro_storeE/.
%%--------------------------------------------

%%-----------------------------------------------
% copyfile *95.94_ev_fleetSize* evFleetEV80/.
% copyfile *95.94_d_fleetSize* dieselFleetEV80/.
% copyfile *60.148_ev_fleetSize* evFleetRenauldMasterZE/.
% copyfile *60.148_d_fleetSize* dieselFleetRenauldMasterZE/.
% copyfile *74.1_ev_fleetSize* evFleeteVito/.
% copyfile *74.1_d_fleetSize* dieselFleeteVito/.
% copyfile *57.17_ev_fleetSize* evFleeteSprinterLowRange/.
% copyfile *57.17_d_fleetSize* dieselFleeteSprinterLowRange/.
% copyfile *74.561_ev_fleetSize* evFleeteSprinterHiRange/.
% copyfile *74.561_d_fleetSize* dieselFleeteSprinterHiRange/.
% copyfile *74.56_ev_fleetSize* evFleeteSprinterHi39TRange/.
% copyfile *74.56_d_fleetSize* dieselFleeteSprinterHi39TRange/.
% copyfile *99.4_ev_fleetSize* evFleetT4/.
% copyfile *99.4_d_fleetSize* dieselFleetT4/.
%%-------------------------------------------------------------

%% Save charging output files (vertical concatenation)
cd 'C:\Users\Sofia\OneDrive - Flexible Power Systems Ltd\dev\Smart_charging_prototypes\Allocation_scripts\Outputs_20200920\allCasesAllocCharging\allCasesVerticalOutputAddedColumns\';
copyfile *new_allCasesVerticalOutputFile* allCasesChargingVerticalOutputs/.

toc