classdef XmlSpecifiedRuleCheck < handle
    %XMLSPECIFIEDRULECHECK This class is doing the parsing of placement rules defined
    %in xml format and then checks individual cells.    
    
    properties(Access=private)
        ruleSetFile;
        ruleSets;
        
        morphologyRuleInstances;
        layerInfo;
        
        results;
        
        yBinsSize; %TODO: offer set function
        layerBins;
        transferFcn;
        ruleCheckFcn;
    end
    properties(Access=public)
        strictness;
    end
    
    methods
        function obj = XmlSpecifiedRuleCheck(file,lInfo)
            obj.ruleSetFile = file;
            obj.layerInfo = lInfo;
            obj.yBinsSize = 10; %micron            
            obj.transferFcn.default = @(x)x;
            obj.transferFcn.upper_hard_limit = @(x)obj.upper_hard_limit(x);
            obj.ruleCheckFcn.region_target = @(instance,rule,bins)obj.checkRegionTarget(instance,rule,bins);
            obj.ruleCheckFcn.below = @(instance,rule,bins)obj.checkYBelow(instance,rule,bins);
            obj.ruleCheckFcn.prefer_unscaled = @(instance,rule,bins)obj.preferUnscaled(instance,rule,bins);
            obj.makeLayerBins();
            obj.strictness = 75;
            obj.morphologyRuleInstances = containers.Map;
            %then do parsing here   
            if(exist('parseXML','file'))
                xml = parseXML(file);
            else
                xml = xml2struct(file);
            end
            obj.addRulesFromXml(xml.Children(cellfun(@(x)x(1)~='#',{xml.Children.Name})));
        end
        function [] = addMorphologyInstance(obj,file)
            %read new rule instances
            if(~exist(file,'file'))
                error('PlacementHints:ReadRuleInstance:AnnotationsNotFound',...
                    'No annotation xml file found at %s. Please annotate before use!',file);
                %[~,morphName] = fileparts(file);                   
                %obj.morphologyRuleInstances(end+1).morphName = morphName;
                %obj.morphologyRuleInstances(end).rules = [];
                %return
            end
            if(exist('parseXML','file'))
                xml = parseXML(file);
            else
                xml = xml2struct(file);
            end           
            ifElseExpansion = @(x,ie)ie{double(x)+1};
            %This relies on lazy evaluation of the if/else condition. If
            %this ever fails just use string returning functions instead of
            %directly returning the string.
            nameFieldLookup = @(x,str,fn)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(cellfun(@(s)strcmp(s,str),{x.Name})).(fn)});
            if(isempty(xml.Attributes))
                warning('PlacementHints:ReadRuleInstance:MorphologyNotSpecified','Morphology name not specified in xml. Guessing from filename: %s',file);
                [~,morphName] = fileparts(file);                
            else
                morphName = nameFieldLookup(xml.Attributes,'morphology','Value');
            end
            
            myStruct.morphName = morphName;
            
            annotations = xml.Children;
            annotations = annotations(cellfun(@(x)strcmp(x,'placement'),{annotations.Name}));
            for i = 1:length(annotations)
                instance = annotations(i).Attributes;
                
                ruleName = nameFieldLookup(instance,'rule','Value');
                myStruct.rules(i).Rule = ruleName;                
                
                otherAttributes = setdiff({instance.Name},'rule');
                for j = 1:length(otherAttributes)
                    myStruct.rules(i).(otherAttributes{j})=nameFieldLookup(instance,otherAttributes{j},'Value');
                end                
            end
            obj.morphologyRuleInstances(morphName) = myStruct;
        end
        function scores = getResult(obj,morphName,inLayer,asMType)            
            scores = obj.checkMorphology(morphName,inLayer,asMType);            
            obj.results(end+1).morphology = morphName;
            obj.results(end).mtype = asMType;
            obj.results(end).scores = scores;
            obj.results(end).layer = inLayer;
        end
        function [] = plotOverview(obj,varargin)
            filter = ones(1,length(obj.results));
            titleStr = '';
            for i = 1:2:length(varargin)
                if(ischar(varargin{i+1}))
                    filter = filter.*cellfun(@(x)strcmp(x,varargin{i+1}),{obj.results.(varargin{i})});
                    titleStr = cat(2,titleStr,sprintf('%s is %s; ',varargin{i:i+1}));
                else
                    filter = filter.*([obj.results.(varargin{i})]==varargin{i+1});
                    titleStr = cat(2,titleStr,sprintf('%s is %d; ',varargin{i:i+1}));
                end                 
            end
            valids = obj.results(find(filter));
            allYBins = catCell(2,obj.layerBins([valids.layer]));
            allScores = catCell(2,{valids.scores});
            figure('Position',[200 300 300 800]);
            boxplot(allScores,allYBins,'plotstyle','compact','orientation','horizontal');
            xlabel('score');ylabel('\mum');set(gca,'XLim',[0 max(get(gca,'XLim'))]);
            axes('Position',get(gca,'Position'),'Color','none','YTick',[],'XAxisLocation','top','XColor',[0.7 0 0]);
            line(cellfun(@(y)sum(allScores(allYBins==y)),num2cell(unique(allYBins))),unique(allYBins),'Color',[1 0 0]);            
            xlabel('total score'); set(gca,'XLim',[0 max(get(gca,'XLim'))],'YLim',[min(allYBins) max(allYBins)]);
            title(titleStr,'Interpreter','none');
        end
        function [] = writeChampions(obj,toFile)
            fid = fopen(toFile,'w');
            layerMType = cellfun(@(x,y)sprintf('Layer %d: %s',x,y),{obj.results.layer},{obj.results.mtype},'UniformOutput',false);
            umtype = unique(layerMType);
            for i = 1:length(umtype)
                fprintf(fid,'For mtype = %s\n',umtype{i});
                indices = find(cellfun(@(x)strcmp(x,umtype{i}),layerMType));                
                if(isempty(indices))
                    continue
                end
                bins = obj.layerBins{obj.results(indices(1)).layer};
                for j = 1:length(bins)
                    [scores sorted] = sort(cellfun(@(x)x(j),{obj.results(indices).scores}));
                    fprintf(fid,'\t%4.2f: %s -- %d\n',bins(j),obj.results(indices(sorted(end))).morphology,scores(end));
                    for k = max(length(scores)+[-1 -2],1)                        
                        fprintf(fid,'\t\t%s -- %d\n',obj.results(indices(sorted(k))).morphology,scores(k));
                    end
                end                
            end
            fclose(fid);
        end
        function [varargout] = writeBestBin(obj,toFile,varargin)
            filter = ones(1,length(obj.results));
            titleStr = '';
            for i = 1:2:length(varargin)
                if(ischar(varargin{i+1}))
                    filter = filter.*cellfun(@(x)strcmp(x,varargin{i+1}),{obj.results.(varargin{i})});
                    titleStr = cat(2,titleStr,sprintf('%s is %s; ',varargin{i:i+1}));
                else
                    filter = filter.*([obj.results.(varargin{i})]==varargin{i+1});
                    titleStr = cat(2,titleStr,sprintf('%s is %d; ',varargin{i:i+1}));
                end                 
            end
            valids = obj.results(find(filter));
            
            if(ischar(toFile))
                fid = fopen(toFile,'w');                        
                fprintf(fid,'Using rule set at %s\n',obj.ruleSetFile);
                fprintf(fid,'and the following layer boundaries:\n');
                for i = 1:length(obj.layerInfo)
                    fprintf(fid,'Layer %d:\n\t\tfrom %4.2f to %4.2f\n',i,obj.layerInfo(i).From,obj.layerInfo(i).To);
                end
            else
                fid = toFile;
            end
            fprintf(fid,'\nShowing results for the following filter(s):\n\t%s\n\n',titleStr);
            for i = 1:length(valids)
                bins = obj.layerBins{valids(i).layer};
                mx = max(valids(i).scores);
                pos = mean(bins(valids(i).scores == mx));
                fprintf(fid,'\t%s: %4.2f -- %d\n',valids(i).morphology, pos, mx);
            end
            if(nargout==1)
                varargout{1} = fid;
            else
                close(fid);
            end
        end
        function [] = plotCollage(obj,morphDir,maxNum,varargin)            
            filter = ones(1,length(obj.results));
            titleStr = '';
            for i = 1:2:length(varargin)
                if(ischar(varargin{i+1}))
                    filter = filter.*cellfun(@(x)strcmp(x,varargin{i+1}),{obj.results.(varargin{i})});
                    titleStr = cat(2,titleStr,sprintf('%s is %s; ',varargin{i:i+1}));
                else
                    filter = filter.*([obj.results.(varargin{i})]==varargin{i+1});
                    titleStr = cat(2,titleStr,sprintf('%s is %d; ',varargin{i:i+1}));
                end                 
            end
            valids = obj.results(find(filter));                        
            for i = 1:length(valids)
                bins = obj.layerBins{valids(i).layer};
                mx(i) = max(valids(i).scores);
                pos(i) = mean(bins(valids(i).scores == mx(i)));                
            end            
            [~, indices] = sort(mx);            
            indices = indices(max(1,end-maxNum+1):end);
            indices = indices(mx(indices)>0);
            mLabels = {valids(indices).morphology};
            pos = pos(indices);
            
            
            mr = bbp_sdk_java.Morphology_Reader;
            mr.open(morphDir);
            morphs = bbp_sdk_java.Morphologies;
            mTgt = bbp_sdk_java.Morphology_Target;
            for i = 1:length(mLabels)
                mTgt.insert(mLabels{i});
            end
            mr.read(morphs,mTgt);
            
            fgr = figure('Position',[200 400 120*length(mLabels) 400]);
            tbl.apical = {3};
            tbl.soma = {3};
            tbl.dend = {3};
            tbl.axon = {2};
            iter = morphs.begin;
            xOff = 0;
            while(~iter.equals(morphs.end))
                m = iter.value;
                index = find(cellfun(@(x)strcmp(x,char(m.label)),mLabels));
                box = getNeuronAABoundingBox(m,'axon');
                plotNeuronColored2(m,tbl,true,true,'colorTable',[0 0 0;0 0 1;1 0 0],'offset',[xOff-box(1) pos(index) 0]);
                xOff = xOff + 25 + diff(box(1:2));
                iter.next;
            end 
            set(gca,'YLim',get(gca,'YLim'));
            for i = 1:length(obj.layerInfo)
                line(get(gca,'XLim'),obj.layerInfo(i).From.*ones(1,2),'Color',[0 0 0],'LineWidth',3);
                line(get(gca,'XLim'),obj.layerInfo(i).To.*ones(1,2),'Color',[0 0 0],'LineWidth',3);
                text(10,(obj.layerInfo(i).From + obj.layerInfo(i).To)/2,num2str(i));
            end
            title(titleStr,'Interpreter','none');
        end
        
    end
    methods(Access=private)        
        function scores = checkMorphology(obj,morphName,inLayer,asMType)                        
            if(~obj.morphologyRuleInstances.isKey(morphName))
                error('PlacementHints:getResults:MorphologyNotAnnotated','Morphology %s has no rule instance file specified!',morphName);
            else
                relevantInstances = obj.morphologyRuleInstances(morphName).rules;
                if(~isfield(obj.ruleSets,asMType))                    
                    relevantRuleSet = [];
                else
                    relevantRuleSet = obj.ruleSets.(asMType); 
                end                
                
                scores = ones(0,length(obj.layerBins{inLayer}));
                for i = 1:length(relevantInstances)
                    if(isempty(relevantRuleSet) || ~relevantRuleSet.rules.isKey(relevantInstances(i).Rule))
                        if(obj.ruleSets.global.rules.isKey(relevantInstances(i).Rule))
                            relevantRule = obj.ruleSets.global.rules(relevantInstances(i).Rule);
                        else
                            error('PlacementHints:getResults:UnknownRule','Rule instance refers to rule %s in %s (morph: %s), which is not defined! Neither defined as global',...
                            relevantInstances(i).Rule,asMType, morphName);
                        end
                    else
                        relevantRule = relevantRuleSet.rules(relevantInstances(i).Rule);
                    end                    
                    if(isfield(relevantInstances(i),'transferFcn'))
                        tferFunc = obj.transferFcn.(strrep(relevantInstances(i).transferFcn,'-','_'));
                    else
                        tferFunc = obj.transferFcn.default;
                    end
                    scores(i,:) = tferFunc(obj.ruleCheckFcn.(relevantRule.type)(relevantInstances(i),relevantRule,obj.layerBins{inLayer}));
                end
                scores = obj.mergeScores(scores);
            end
        end
        
        function scores = mergeScores(obj,scores)  
            if(isempty(scores))
                scores = ones(1,size(scores,2));
                return;
            end            
            baseWeight = log10(obj.strictness).^9;
            epsilon = 1/baseWeight;
            %fcn = @(x,p)(baseWeight.*nansum((nansum(real(x).^p)/sum(~isnan(real(x))))^(1/p)));
            fcn = @(x,p)nansum((nansum(real(baseWeight.*(x+epsilon)).^p)/sum(~isnan(real(x))))^(1/p));
            shapeParameter = 5-obj.strictness/12.5;
            scores = ceil((cellfun(@(x)fcn(x,shapeParameter),num2cell(scores,1))+1).*min(imag(scores),[],1));%+ones(1,size(scores,2)));
        end              
        
        
        %Function subject to change if we ever inplement more than just y
        %intervals. For now lazily implemented
        function interval = getLayerInterval(obj,rule,fields)
            fractionLookup = @(iv,f)iv(1)+f*diff(iv);
            getIv = @(x)cat(2,obj.layerInfo(x).From,obj.layerInfo(x).To);
            
            iv = cellfun(@(str)getIv(str2double(rule.(cat(2,str,'_layer')))),fields,'UniformOutput',false);
            f = cellfun(@(str)str2double(rule.(cat(2,str,'_fraction'))),fields,'UniformOutput',false);
            interval = cellfun(fractionLookup,iv,f);
            %l = cat(1,str2double(rule.y_min_layer), str2double(rule.y_max_layer));
            %f = cat(1,str2double(rule.y_min_fraction), str2double(rule.y_max_fraction));
            %interval = cat(2,fractionLookup(getIv(l(1)),f(1)),fractionLookup(getIv(l(2)),f(2)));
        end                      
        
        function [] = addRulesFromXml(obj,xml)
            ifElseExpansion = @(x,ie)ie{double(x)+1};
            %This relies on lazy evaluation of the if/else condition. If
            %this ever fails just use string returning functions instead of
            %directly returning the string.
            nameValueLookup = @(x,str)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(cellfun(@(s)strcmp(s,str),{x.Name})).Value});
            
            for i = 1:length(xml)
                if(strcmp(xml(i).Name,'global_rule_set'))
                    currMType = 'global';
                else
                    currMType = nameValueLookup(xml(i).Attributes,'mtype');
                end
                obj.ruleSets.(currMType).mtype = currMType;
                myMap = containers.Map;
                %If we ever have other types of rules add that case here.
                rules = xml(i).Children;
                rules = rules(cellfun(@(x)x(1)~='#',{rules.Name}));
                for j = 1:length(rules)
                    id = nameValueLookup(rules(j).Attributes,'id');
                    myStruct = struct();
                    if(isempty(id))
                        error('XMLPlacementHints:Rules:EmptyIdentifier','This rule has no field "id" specified!');
                    end
                    attr = setdiff({rules(j).Attributes.Name},'id');
                    for k=1:length(attr)
                        myStruct.(attr{k}) = nameValueLookup(rules(j).Attributes,attr{k});                        
                    end
                    myMap(id) = myStruct;
                end
                obj.ruleSets.(currMType).rules = myMap;
            end
        end
        
        function [] = makeLayerBins(obj)            
            for i = 1:length(obj.layerInfo)
                borders = linspace(obj.layerInfo(i).From,obj.layerInfo(i).To,...
                    ceil((obj.layerInfo(i).To-obj.layerInfo(i).From)/obj.yBinsSize)+1);
                obj.layerBins{i} = (borders(1:end-1) + borders(2:end))./2;
            end
        end
        
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        %      Specific functions for different rule types       %
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        function scores = preferUnscaled(obj,instance,rule,bins)
            variance = str2double(rule.sigma);
            scores = NaN + ones(size(bins)).*...
                (normpdf(str2double(instance.percentage),0,variance)/normpdf(0,0,variance))*1j;
        end
        function scores = checkRegionTarget(obj,instance,rule,bins)           
            %minMaxFcn = @(x,y)cat(2,max(x(1),y(1)),min(x(2),y(2)));
            intervalAbs = obj.getLayerInterval(rule,{'y_min','y_max'}); 
            intervalRel = [str2double(instance.y_min) str2double(instance.y_max)];            
            meanAbs = mean(intervalAbs);
            sigAbs = diff(intervalAbs)/3;
            meanRel = mean(intervalRel);
            sigRel = diff(intervalRel)/3;
            xMin = min(meanRel-3*sigRel+min(bins),meanAbs-3*sigAbs);
            xMax = max(meanRel+3*sigRel+min(bins),meanAbs+3*sigAbs);
            x = xMin:10:xMax;                               
            func = @(off)sum(normpdf(x,meanRel+off,sigRel).*normpdf(x,meanAbs,sigAbs));
            scores = cellfun(func,num2cell(bins))./func(min(intervalAbs)-min(intervalRel));
            scores(scores>1)=1;
            
            %scores = cellfun(@(x)diff(minMaxFcn(intervalAbs,intervalRel+x)),num2cell(bins))./min(diff(intervalAbs),diff(intervalRel));
            %scores(scores<0)=0;
            scores = scores + ones(size(scores))*1i;
        end
        function scores = checkYBelow(obj,instance,rule,bins)            
            limitAbs = obj.getLayerInterval(rule,{'y'});
            limitRel = str2double(instance.y_max);
            scores = (limitAbs - (limitRel+bins) + 30)./30;
            scores(scores>1) = 1;
            scores(scores<0) = 0;
            scores = NaN + scores.*1i;
        end
        
    end
    
    
    methods(Static=true)
        %Implement transfer functions here
        function dat = upper_hard_limit(dat)
            dat(find(dat(2:end)<dat(1:end-1))+1)=0;
        end        
    end
end

